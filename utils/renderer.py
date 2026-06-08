import re
import html as html_module

from utils.macrotemas import MACROTEMA_SECOES
from utils.maps import gerar_mapa_regiao, render_mapa_geografico
from utils.contentful import obter_url_mapa_contentful
from utils.tables import render_tabela_resumo


FALLBACK_DOC_TEXT = """deu erro.
"""

TEMPLATE_STRING = """
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Data Nordeste – Relatório modelo</title>
    <style>
        @page {
            margin: 16mm 8mm 16mm;
            @bottom-left {
                content: "Relatório automático do Data Nordeste";
                color: #2d2e33;
                font-family: Arial, sans-serif;
                font-size: 10px;
                vertical-align: middle;
                border-top: 1px solid #e4e4e7;
                padding-top: 4mm;
            }
            @bottom-right {
                content: counter(page, decimal-leading-zero);
                color: #2d2e33;
                font-family: Arial, sans-serif;
                font-size: 10px;
                vertical-align: middle;
                border-top: 1px solid #e4e4e7;
                padding-top: 4mm;
            }
        }
        body {
            font-family: Georgia, "Times New Roman", serif;
            max-width: 920px;
            margin:0 auto 2px;
            padding: 0 24px;
            line-height: 1.48;
            font-size: 16px;
            color: #222;
        }
        h1 {
            font-size: 30px;
            font-weight: 700;
            margin: 0 0 14px 0;
        }
        h2 {
            font-size: 24px;
            font-weight: 700;
            margin: 30px 0 10px 0;
        }
        p {
            margin: 0 0 14px 0;
            text-align: justify;
        }
        .field {
            font-size: 17px;
            margin-bottom: 8px;
        }
        .field strong {
            font-weight: 700;
        }
        .indent {
            text-indent: 1.5em;
        }
        ul {
            margin: 8px 0 16px 28px;
        }
        li {
            margin-bottom: 6px;
        }
        .doc-content p {
            font-family: Arial, sans-serif;
            text-indent: 0;
        }
        .doc-content p.lead {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 18px;
            font-style: italic;
            line-height: 1.38;
            color: #3d3d3d;
            margin: 10px 0 24px;
        }
        .doc-content h1 {
            font-size: 34px;
            font-weight: 700;
            margin: 0 0 18px 0;
        }
        .doc-content ul {
            text-indent: 0;
        }
        .section-heading {
            display: grid;
            grid-template-columns: auto 1fr;
            align-items: end;
            column-gap: 16px;
            margin: 14px 0 10px;
        }
        .section-number {
            color: #c68a2c;
            font-size: 56px;
            line-height: 0.9;
            font-weight: 400;
        }
        .section-title-wrap {
            padding-bottom: 7px;
            border-bottom: 1px solid #d99a37;
        }
        .section-title {
            color: #255235;
            font-size: 29px;
            line-height: 1;
            font-weight: 400;
        }
        .chart-block {
            margin: 18px auto 20px;
            text-align: center;
            break-inside: avoid;
        }
        .chart-block img {
            display: block;
            max-width: 78%;
            height: auto;
            margin: 0 auto;
        }
        .figure-caption {
            margin: 8px auto 16px;
            max-width: 76%;
            color: #333;
            font-family: Arial, sans-serif;
            font-size: 13px;
            line-height: 1.35;
            text-align: center;
        }
        .map-block {
            width: 100%;
            max-width: 420px;
            margin: 16px auto 22px;
            break-inside: avoid;
            text-align: center;
            overflow: hidden;
            border: 1px solid #b9b9b9;
            background: #f7f7f7;
            padding: 6px 6px 4px;
        }
        .map-block--region {
            max-width: 760px;
            margin: 18px 0 20px;
            border: 0;
            background: transparent;
            padding: 0;
            text-align: left;
        }
        .region-map-title {
            margin: 0 0 12px;
            color: #006b3f;
            font-family: Arial, sans-serif;
            font-size: 17px;
            font-weight: 400;
            line-height: 1.2;
        }
        .region-map-image {
            display: block;
            width: 100%;
            height: auto;
        }
        .map-title {
            color: #111;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.2;
            margin: 0 0 4px;
            text-align: center;
        }
        .map-frame {
            width: 100%;
            aspect-ratio: 220 / 194;
            height: auto;
            border: 1px solid #c8d6dd;
            box-sizing: border-box;
            overflow: hidden;
            background: #bfe3f1;
            position: relative;
        }
        .locator-map {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .map-block figcaption {
            margin-top: 4px;
            color: #111;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.2;
        }
        .locator-label {
            position: absolute;
            transform: translate(-100%, -50%);
            margin-left: -8px;
            color: #111;
            font: 700 12px Arial, sans-serif;
            text-shadow: 0 1px 2px #fff, 0 -1px 2px #fff, 1px 0 2px #fff, -1px 0 2px #fff;
            white-space: nowrap;
            pointer-events: none;
        }
        .state-label {
            position: absolute;
            transform: translate(-50%, -50%);
            color: #111;
            font: 700 9px Arial, sans-serif;
            line-height: 1;
            text-shadow: 0 1px 2px #fff, 0 -1px 2px #fff, 1px 0 2px #fff, -1px 0 2px #fff;
            pointer-events: none;
        }
        .locator-dot {
            position: absolute;
            width: 9px;
            height: 9px;
            transform: translate(-50%, -50%);
            border: 1.5px solid #8f1d14;
            border-radius: 999px;
            background: #d7191c;
            box-sizing: border-box;
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.75);
            pointer-events: none;
        }
        .region-legend {
            display: grid;
            grid-template-columns: repeat(2, max-content);
            gap: 4px 12px;
            justify-content: center;
            margin: 7px 0 3px;
            font-family: Arial, sans-serif;
            font-size: 11px;
            color: #111;
        }
        .region-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            white-space: nowrap;
        }
        .region-legend-swatch {
            width: 10px;
            height: 10px;
            border: 1px solid rgba(0, 0, 0, 0.35);
            border-radius: 2px;
        }
        .map-fallback {
            display: grid;
            gap: 6px;
            place-items: center;
            min-height: 220px;
            border: 1px solid #d8d0bf;
            background: #f5f0e8;
            color: #255235;
            font-family: Arial, sans-serif;
        }
        .map-fallback a {
            color: #bd6039;
            font-size: 13px;
            font-weight: 700;
        }
        .report-cover {
            margin: 0 0 34px;
            font-family: Arial, sans-serif;
            color: #25262a;
            break-inside: avoid;
        }
       .cover-header {
    width: 100vw;
    height: 10%;
    margin-left: calc(50% - 50vw);
    margin-right: calc(50% - 50vw);
    margin-bottom: 24px;
    padding: 12px 24px;
    background: #eeeeef;
    box-sizing: border-box;
}
        .cover-meta {
            position: relative;
            display: flex;
            justify-content:right;
            align-items: right;
            margin-bottom: 0;
            font-size: 14px;
        }
        .cover-brand {
    position: absolute;
    left: 0;
    display: inline-grid;
    gap: 2px;
    line-height: 1;
}
        .brand-mark {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: #008d43;
            font-size: 26px;
            font-weight: 900;
            letter-spacing: 0;
        }
        .brand-squares {
            display: grid;
            grid-template-columns: repeat(3, 4px);
            gap: 2px;
        }
        .brand-squares span {
            width: 4px;
            height: 4px;
        }
        .brand-squares span:nth-child(1),
        .brand-squares span:nth-child(5) { background: #ef7d00; }
        .brand-squares span:nth-child(2),
        .brand-squares span:nth-child(6) { background: #0a8f43; }
        .brand-squares span:nth-child(3),
        .brand-squares span:nth-child(4) { background: #204f9e; }
        .brand-subtitle {
            color: #222;
            font-size: 5px;
            font-weight: 700;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .pdf-page-header {
            display: none;
        }
        .pdf-page-header-brand {
            display: inline-grid;
            gap: 2px;
            line-height: 1;
        }
        .pdf-page-header-mark {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: #111;
            font-size: 26px;
            font-weight: 900;
            letter-spacing: 0;
        }
        .pdf-page-header-subtitle {
            color: #222;
            font-size: 5px;
            font-weight: 700;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .cover-date {
            color: #2f3033;
            font-size: 14px;
            white-space: nowrap;
            text-align: center;
            transform: translateY(6px);
        }
        .cover-content {
            padding: 0;
        }
        .cover-kicker {
            margin-bottom: 10px;
            color: #005e2f;
            font-size: 16px;
            font-weight: 500;
        }
        .cover-city {
            margin: 0 0 24px;
            color: #2b2c30;
            font-family: Arial, sans-serif;
            font-size: 34px;
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: 0;
        }
        .cover-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 22px;
            margin-bottom: 26px;
        }
        .metric-card {
            min-height: 120px;
            padding: 13px 12px 10px;
            border: 1px solid #e7e7ea;
            border-radius: 8px;
            background: linear-gradient(
        to bottom,
        #f5f5f6 0%,
        #f5f5f6 42%,
        #ffffff 42%,
        #ffffff 100%
    );
            box-shadow: 0 8px 18px rgba(23, 28, 38, 0.06);
            box-sizing: border-box;
        }
        .metric-heading {
            display: grid;
            grid-template-columns: 18px 1fr;
            gap: 8px;
            align-items: center;
            margin-bottom: 11px;
        }
        .metric-icon {
            width: 18px;
            height: 18px;
            color: #008d43;
        }
        .metric-label {
            color: #1f2227;
            font-size: 15px;
            font-weight: 700;
            line-height: 1.15;
        }
        .metric-source {
            margin-top: 4px;
            color: #8a8d95;
            font-size: 11px;
            line-height: 1.1;
        }
        .metric-value {
            color: #008d43;
            font-family: Arial, sans-serif;
            font-size: 21px;
            font-weight: 800;
            line-height: 1;
            white-space: nowrap;
        }
        .metric-unit {
            font-size: 15px;
            font-weight: 800;
        }
        .metric-caption {
            margin-top: 30px;
            color: #8a8d95;
            font-size: 10px;
            line-height: 1.1;
        }
        .region-radar-title {
            margin: -4px 0 12px;
            color: #005e2f;
            font-size: 16px;
            font-weight: 500;
            line-height: 1.2;
        }
        .region-radar-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
            gap: 22px;
            margin-bottom: 16px;
        }
        .region-radar-card {
            min-height: 260px;
            padding: 18px;
            border-radius: 12px;
            background: #f7f7f8;
            box-sizing: border-box;
        }
        .score-column {
            display: grid;
            gap: 14px;
            align-content: start;
        }
        .region-radar-chart {
            display: block;
            width: 100%;
            height: 224px;
        }
        .radar-grid {
            fill: none;
            stroke: #333;
            stroke-width: 0.8;
        }
        .radar-axis {
            stroke: #555;
            stroke-width: 0.75;
        }
        .radar-area {
            fill: #008d43;
            fill-opacity: 0.22;
            stroke: #008d43;
            stroke-width: 2;
        }
        .radar-label {
            fill: #1f2227;
            font-family: Arial, sans-serif;
            font-size: 10px;
        }
        .radar-tick {
            fill: #6f737b;
            font-family: Arial, sans-serif;
            font-size: 8px;
        }
        .score-card {
            grid-column: 3 / span 2;
            overflow: hidden;
            border: 1px solid #e3e3e7;
            border-radius: 22px;
            background: #fff;
            box-shadow: 0 8px 18px rgba(23, 28, 38, 0.05);
        }
        .score-header {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 18px 24px;
            background: #f5f5f6;
        }
        .score-icon {
            width: 24px;
            height: 24px;
            color: #008d43;
            flex: 0 0 auto;
        }
        .score-title {
            color: #24252a;
            font-size: 19px;
            font-weight: 500;
            line-height: 1.2;
        }
        .score-body {
            padding: 16px 24px 18px;
        }
        .score-line {
            display: flex;
            align-items: baseline;
            gap: 18px;
            margin-bottom: 12px;
        }
        .score-value {
            color: #ff9900;
            font-size: 34px;
            font-weight: 800;
            line-height: 1;
            white-space: nowrap;
        }
        .score-max {
            font-size: 20px;
            font-weight: 700;
        }
        .score-status {
            color: #2a2b30;
            font-size: 20px;
            font-weight: 600;
            line-height: 1.2;
        }
        .score-description {
            margin: 0;
            color: #8a8d95;
            font-size: 12px;
            line-height: 1.35;
            text-align: left;
        }
        .score-support-text {
            grid-column: 3 / span 2;
            margin: -2px 0 0;
            color: #2d2e33;
            font-size: 12px;
            line-height: 1.36;
            text-align: left;
        }
        .score-legend {
            grid-column: 1 / -1;
            margin-top: 6px;
        }
        .score-legend-title {
            margin: 0 0 10px;
            color: #2d2e33;
            font-size: 20px;
            font-weight: 500;
            line-height: 1.2;
        }
        .score-legend-bar {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            overflow: hidden;
            border-radius: 7px;
        }
        .score-legend-item {
            padding: 8px 16px;
            color: #fff;
            font-size: 18px;
            font-weight: 500;
            line-height: 1;
            white-space: nowrap;
        }
        .score-legend-item + .score-legend-item {
            border-left: 2px solid #fff;
        }
        .score-legend-very-high { background: #6f8f18; }
        .score-legend-high { background: #ff9f0a; }
        .score-legend-low { background: #eb5b0c; }
        .score-legend-very-low { background: #c91423; }
        .macrotheme-card {
            grid-column: 1 / -1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
            min-height: 72px;
            margin-top: 10px;
            padding: 14px 26px;
            border-left: 4px solid #ff3045;
            border-radius: 18px 0 0 18px;
            background: #f7f7f8;
            box-sizing: border-box;
        }
        .macrotheme-title {
            display: inline-flex;
            align-items: center;
            gap: 16px;
            min-width: 0;
        }
        .macrotheme-icon-box {
            display: inline-grid;
            place-items: center;
            width: 28px;
            height: 28px;
            border: 3px solid #ff3045;
            color: #ff3045;
            box-sizing: border-box;
        }
        .macrotheme-icon {
            width: 18px;
            height: 18px;
        }
        .macrotheme-name {
            color: #2d2e33;
            font-size: 26px;
            font-weight: 800;
            line-height: 1;
        }
        .macrotheme-status {
            padding: 8px 14px;
            border-radius: 6px;
            background: #6f8f18;
            color: #fff;
            font-size: 13px;
            font-weight: 500;
            line-height: 1;
            white-space: nowrap;
        }
        .macrotheme-summary {
            grid-column: 1 / -1;
            margin: -2px 0 0;
        }
        .macrotheme-summary-title {
            margin: 0 0 12px;
            color: #005e2f;
            font-size: 16px;
            font-weight: 500;
            line-height: 1.2;
        }
        .macrotheme-summary-text {
            margin: 0;
            color: #2d2e33;
            font-size: 13px;
            line-height: 1.42;
            text-align: left;
        }
        .indicator-scores {
            grid-column: 1 / -1;
            margin-top: 4px;
        }
        .indicator-scores-title {
            margin: 0 0 12px;
            color: #005e2f;
            font-size: 16px;
            font-weight: 500;
            line-height: 1.2;
        }
        .indicator-score-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px 28px;
        }
        .indicator-score-card {
            display: grid;
            grid-template-columns: 22px minmax(0, 1fr) auto;
            align-items: center;
            gap: 12px;
            min-height: 66px;
            padding: 10px 14px;
            border: 1px solid #eeeef1;
            border-radius: 10px;
            background: #f8f8f9;
            box-shadow: 0 6px 14px rgba(23, 28, 38, 0.04);
            box-sizing: border-box;
        }
        .indicator-icon {
            width: 18px;
            height: 18px;
            color: #ff3045;
        }
        .indicator-name {
            color: #22242a;
            font-size: 12px;
            font-weight: 600;
            line-height: 1.15;
        }
        .indicator-source {
            margin-top: 4px;
            color: #8a8d95;
            font-size: 8px;
            line-height: 1.1;
        }
        .indicator-badge {
            min-width: 42px;
            padding: 7px 9px;
            border-radius: 7px;
            color: #fff;
            font-size: 12px;
            font-weight: 800;
            line-height: 1;
            text-align: center;
            white-space: nowrap;
        }
        .indicator-badge-very-high { background: #6f8f18; }
        .indicator-badge-high { background: #ff9f0a; }
        .indicator-badge-low { background: #eb5b0c; }
        .indicator-badge-very-low { background: #c91423; }
        .indicator-badge-unknown { background: #9a9da5; }
        .pdf-footer {
            display: none;
        }
        .pdf-footer-page::before {
            content: counter(page, decimal-leading-zero);
        }
        .theme-detail-page {
            page-break-before: always;
            break-before: page;
            font-family: Arial, sans-serif;
            color: #26272c;
        }
        .theme-detail-header {
            display: none;
        }
        .theme-detail-header .cover-brand {
            position: static;
        }
        .theme-detail-kicker {
            margin: 0 0 20px;
            color: #8a8d95;
            font-size: 14px;
            line-height: 1.2;
        }
        .theme-detail-title {
            margin: 0 0 18px;
            color: #005e2f;
            font-family: Arial, sans-serif;
            font-size: 18px;
            font-weight: 600;
            line-height: 1.2;
        }
        .theme-detail-text {
            margin: 0 0 18px;
            color: #2d2e33;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.48;
            text-align: left;
        }
        @media print {
            html,
            body {
                width: auto;
                max-width: none;
                margin: 0;
                padding: 0;
                background: #fff;
            }
            body {
                font-size: 11px;
                line-height: 1.35;
            }
            .cover-header {
                display: none;
            }
            .theme-detail-header {
                display: none;
            }
            .pdf-page-header {
                position: fixed;
                top: -16mm;
                left: -8mm;
                right: -8mm;
                display: block;
                width: auto;
                height: 12mm;
                padding: 2.5mm 14mm;
                background: #eeeeef;
                box-sizing: border-box;
                font-family: Arial, sans-serif;
                z-index: 1000;
            }
            .pdf-page-header-brand {
                display: block;
                width: 22mm;
                height: 8mm;
            }
            .pdf-page-header-logo {
                display: block;
                width: 22mm;
                height: 8mm;
            }
            .report-cover,
            .theme-detail-page,
            .doc-content {
                width: 100%;
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            .report-cover {
                break-after: auto;
                page-break-after: auto;
                break-inside: auto;
                page-break-inside: auto;
            }
            .cover-kicker {
                margin-bottom: 9px;
                font-size: 15px;
            }
            .cover-city {
                margin-bottom: 18px;
                font-size: 34px;
            }
            .cover-metrics {
                display: flex;
                flex-wrap: wrap;
                gap: 0;
                margin-bottom: 0;
            }
            .metric-card {
                width: 23.5%;
                min-height: 112px;
                margin: 0 1.5% 18px 0;
                padding: 14px 13px 12px;
                border-radius: 7px;
                box-shadow: none;
            }
            .metric-card:nth-of-type(4) {
                margin-right: 0;
            }
            .metric-heading {
                display: flex;
                gap: 8px;
                align-items: center;
                margin-bottom: 12px;
            }
            .metric-icon {
                width: 17px;
                height: 17px;
            }
            .metric-label {
                font-size: 12px;
            }
            .metric-source,
            .metric-caption {
                font-size: 8px;
            }
            .metric-caption {
                margin-top: 32px;
            }
            .metric-value {
                font-size: 20px;
            }
            .metric-unit {
                font-size: 13px;
            }
            .score-card {
                width: 100%;
                margin: 0 0 12px;
                border-radius: 14px;
                box-shadow: none;
            }
            .region-radar-title {
                width: 100%;
                margin: 0 0 8px;
                font-size: 13px;
            }
            .region-radar-row {
                display: flex;
                gap: 0;
                margin-bottom: 14px;
            }
            .region-radar-card {
                width: 48.5%;
                min-height: 205px;
                margin: 0 3% 0 0;
                padding: 12px;
                border-radius: 10px;
            }
            .score-column {
                display: block;
                width: 48.5%;
            }
            .region-radar-chart {
                height: 181px;
            }
            .radar-label {
                font-size: 8px;
            }
            .radar-tick {
                font-size: 6px;
            }
            .score-header {
                gap: 12px;
                padding: 18px 20px;
            }
            .score-icon {
                width: 21px;
                height: 21px;
            }
            .score-title {
                font-size: 18px;
            }
            .score-body {
                padding: 18px 20px 20px;
            }
            .score-line {
                gap: 14px;
                margin-bottom: 10px;
            }
            .score-value {
                font-size: 32px;
            }
            .score-max,
            .score-status {
                font-size: 18px;
            }
            .score-description,
            .score-support-text {
                font-size: 12px;
                line-height: 1.38;
            }
            .score-support-text {
                width: 100%;
                margin: 0;
            }
            .score-legend {
                width: 100%;
                margin-top: 8px;
            }
            .score-legend-title {
                margin-bottom: 7px;
                font-size: 13px;
            }
            .score-legend-item {
                display: inline-block;
                width: 25%;
                box-sizing: border-box;
                padding: 9px 10px;
                font-size: 11px;
            }
            .macrotheme-card {
                width: 100%;
                min-height: 84px;
                margin-top: 18px;
                padding: 18px 22px;
                border-radius: 14px 0 0 14px;
                box-shadow: none;
            }
            .macrotheme-icon-box {
                width: 26px;
                height: 26px;
                border-width: 2px;
            }
            .macrotheme-icon {
                width: 17px;
                height: 17px;
            }
            .macrotheme-name {
                font-size: 24px;
            }
            .macrotheme-status {
                padding: 7px 12px;
                font-size: 11px;
            }
            .macrotheme-summary-title,
            .indicator-scores-title {
                margin-bottom: 10px;
                font-size: 14px;
            }
            .macrotheme-summary,
            .indicator-scores {
                width: 100%;
            }
            .macrotheme-summary-text {
                font-size: 12px;
                line-height: 1.5;
            }
            .indicator-scores {
                margin-top: 16px;
            }
            .indicator-score-grid {
                display: flex;
                flex-wrap: wrap;
                gap: 0;
            }
            .indicator-score-card {
                width: 31.5%;
                min-height: 82px;
                display: flex;
                align-items: center;
                gap: 10px;
                margin: 0 1.75% 16px 0;
                padding: 13px 14px;
                border-radius: 9px;
                box-shadow: none;
            }
            .indicator-score-card:nth-child(3n) {
                margin-right: 0;
            }
            .indicator-icon {
                flex: 0 0 auto;
                width: 16px;
                height: 16px;
            }
            .indicator-score-card > div {
                flex: 1 1 auto;
                min-width: 0;
            }
            .indicator-name {
                font-size: 11px;
            }
            .indicator-source {
                margin-top: 4px;
                font-size: 7px;
            }
            .indicator-badge {
                flex: 0 0 auto;
                min-width: 36px;
                padding: 7px 8px;
                border-radius: 6px;
                font-size: 11px;
            }
            .score-card,
            .score-legend,
            .macrotheme-card,
            .macrotheme-summary,
            .indicator-scores,
            .indicator-score-card,
            .metric-card,
            .chart-block,
            .map-block {
                break-inside: avoid;
                page-break-inside: avoid;
            }
            .theme-detail-page {
                break-before: page;
                page-break-before: always;
            }
            .theme-detail-kicker {
                display: none;
            }
            .theme-detail-title {
                margin: 0 0 10px;
                font-size: 14px;
            }
            .theme-detail-text {
                margin-bottom: 12px;
                font-size: 10px;
                line-height: 1.45;
            }
            .doc-content {
                break-before: auto;
                page-break-before: auto;
                margin-top: 14px;
            }
            .doc-content h1,
            .doc-content h2 {
                font-family: Arial, sans-serif;
                color: #005e2f;
                break-after: avoid;
                page-break-after: avoid;
            }
            .doc-content h1 {
                font-size: 18px;
            }
            .doc-content h2 {
                font-size: 15px;
            }
            .doc-content p,
            .doc-content li {
                font-size: 10px;
                line-height: 1.42;
            }
            .chart-block {
                margin: 10px auto 12px;
            }
            .chart-block img {
                max-width: 70%;
            }
            .figure-caption {
                font-size: 8px;
            }
        }
        @media (max-width: 760px) {
            .cover-metrics {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .score-card {
                grid-column: 1 / -1;
            }
            .score-support-text {
                grid-column: 1 / -1;
                font-size: 18px;
            }
            .score-legend-bar {
                grid-template-columns: 1fr;
            }
            .score-legend-item + .score-legend-item {
                border-left: 0;
                border-top: 2px solid #fff;
            }
            .macrotheme-card {
                align-items: flex-start;
                flex-direction: column;
            }
            .macrotheme-status {
                white-space: normal;
            }
            .indicator-score-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
<div class="pdf-page-header">
    <div class="pdf-page-header-brand" aria-label="Data Nordeste">
        <svg class="pdf-page-header-logo" viewBox="0 0 150 58" role="img" aria-label="Data Nordeste">
            <rect x="0" y="0" width="150" height="58" fill="none"/>
            <rect x="7" y="14" width="6" height="6" fill="#ef7d00"/>
            <rect x="17" y="14" width="6" height="6" fill="#0a8f43"/>
            <rect x="27" y="14" width="6" height="6" fill="#204f9e"/>
            <rect x="7" y="24" width="6" height="6" fill="#204f9e"/>
            <rect x="17" y="24" width="6" height="6" fill="#ef7d00"/>
            <rect x="27" y="24" width="6" height="6" fill="#0a8f43"/>
            <text x="39" y="31" fill="#008d43" font-family="Arial, sans-serif" font-size="31" font-weight="900">NE</text>
            <text x="7" y="48" fill="#222" font-family="Arial, sans-serif" font-size="6" font-weight="700">DATA NORDESTE</text>
        </svg>
    </div>
</div>
<section class="report-cover">
    <div class="cover-header">
        <div class="cover-meta">
            <div class="cover-brand" aria-label="Data Nordeste">
                <div class="brand-mark">
                    <span class="brand-squares" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span></span>
                    <span>NE</span>
                </div>
                <span class="brand-subtitle">Data Nordeste</span>
            </div>
            <span class="cover-date">{{ cover.data_extenso }}</span>
        </div>
    </div>
    <div class="cover-content">
        <div class="cover-kicker">Relatório geral</div>
        <h1 class="cover-city">{{ cover.cidade_nome }}{% if cover.uf %} ({{ cover.uf }}){% endif %}</h1>
        <div class="cover-metrics">
            {% for metrica in cover.metricas %}
            <div class="metric-card">
                <div class="metric-heading">
                    <svg class="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M4 17h16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                        <path d="M7 15l3.1-4.2 2.7 2.8 3.3-5.1L20 15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                        <circle cx="10.1" cy="10.8" r="1.1" fill="currentColor"/>
                        <circle cx="12.8" cy="13.6" r="1.1" fill="currentColor"/>
                        <circle cx="16.1" cy="8.5" r="1.1" fill="currentColor"/>
                    </svg>
                    <div>
                        <div class="metric-label">{{ metrica.rotulo }}</div>
                        <div class="metric-source">{{ metrica.fonte }}</div>
                    </div>
                </div>
                <div class="metric-value">{{ metrica.valor }}{% if metrica.sufixo %} <span class="metric-unit">{{ metrica.sufixo }}</span>{% endif %}</div>
                <div class="metric-caption">{{ metrica.caption }}</div>
            </div>
            {% endfor %}
        </div>
            <h2 class="region-radar-title">Radar da região</h2>
            <div class="region-radar-row">
            <div class="region-radar-card" aria-label="Radar da região">
                <svg class="region-radar-chart" viewBox="0 0 360 260" role="img" aria-label="Gráfico radar da região">
                    <g transform="translate(180 132)">
                        <polygon fill="none" stroke="#333" stroke-width="0.8" points="0,-82 71,-41 71,41 0,82 -71,41 -71,-41"/>
                        <polygon fill="none" stroke="#333" stroke-width="0.8" points="0,-65.6 56.8,-32.8 56.8,32.8 0,65.6 -56.8,32.8 -56.8,-32.8"/>
                        <polygon fill="none" stroke="#333" stroke-width="0.8" points="0,-49.2 42.6,-24.6 42.6,24.6 0,49.2 -42.6,24.6 -42.6,-24.6"/>
                        <polygon fill="none" stroke="#333" stroke-width="0.8" points="0,-32.8 28.4,-16.4 28.4,16.4 0,32.8 -28.4,16.4 -28.4,-16.4"/>
                        <polygon fill="none" stroke="#333" stroke-width="0.8" points="0,-16.4 14.2,-8.2 14.2,8.2 0,16.4 -14.2,8.2 -14.2,-8.2"/>
                        <line stroke="#555" stroke-width="0.75" x1="0" y1="0" x2="0" y2="-82"/>
                        <line stroke="#555" stroke-width="0.75" x1="0" y1="0" x2="71" y2="-41"/>
                        <line stroke="#555" stroke-width="0.75" x1="0" y1="0" x2="71" y2="41"/>
                        <line stroke="#555" stroke-width="0.75" x1="0" y1="0" x2="0" y2="82"/>
                        <line stroke="#555" stroke-width="0.75" x1="0" y1="0" x2="-71" y2="41"/>
                        <line stroke="#555" stroke-width="0.75" x1="0" y1="0" x2="-71" y2="-41"/>
                        <polygon points="0,-49.2 42.6,-24.6 28.4,16.4 0,65.6 -42.6,24.6 -28.4,-16.4" fill="#008d43" fill-opacity="0.22" stroke="#008d43" stroke-width="2"/>
                        <text class="radar-tick" x="4" y="-65">4</text>
                        <text class="radar-tick" x="4" y="-49">3</text>
                        <text class="radar-tick" x="4" y="-33">2</text>
                        <text class="radar-tick" x="4" y="-17">1</text>
                        <text class="radar-label" x="0" y="-99" text-anchor="middle">Saúde</text>
                        <text class="radar-label" x="94" y="-48" text-anchor="start">Educação</text>
                        <text class="radar-label" x="92" y="38" text-anchor="start">Desenvolvimento</text>
                        <text class="radar-label" x="92" y="51" text-anchor="start">Social</text>
                        <text class="radar-label" x="48" y="97" text-anchor="start">Economia e Renda</text>
                        <text class="radar-label" x="0" y="112" text-anchor="middle">Demografia</text>
                        <text class="radar-label" x="-92" y="75" text-anchor="middle">Infraestrutura e</text>
                        <text class="radar-label" x="-92" y="88" text-anchor="middle">Saneamento</text>
                        <text class="radar-label" x="-105" y="20" text-anchor="end">Meio Ambiente</text>
                        <text class="radar-label" x="-88" y="-47" text-anchor="end">Segurança Hídrica</text>
                    </g>
                </svg>
            </div>
            <div class="score-column">
            <div class="score-card">
                <div class="score-header">
                    <svg class="score-icon" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M4 16l5-5 4 4 6-7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M15 8h4v4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <div class="score-title">Score geral em relação ao Brasil</div>
                </div>
                <div class="score-body">
                    <div class="score-line">
                        <div class="score-value">{{ cover.score.valor }}<span class="score-max">/{{ cover.score.maximo }}</span></div>
                        <div class="score-status">{{ cover.score.status }}</div>
                    </div>
                    <p class="score-description">{{ cover.score.descricao }}</p>
                </div>
            </div>
            <p class="score-support-text">{{ cover.score.texto_apoio }}</p>
            </div>
            </div>
            <div class="score-legend">
                <p class="score-legend-title">Legenda</p>
                <div class="score-legend-bar" aria-label="Legenda do score">
                    <div class="score-legend-item score-legend-very-high">Muito acima da média</div>
                    <div class="score-legend-item score-legend-high">Acima da média</div>
                    <div class="score-legend-item score-legend-low">Abaixo da média</div>
                    <div class="score-legend-item score-legend-very-low">Muito abaixo da média</div>
                </div>
            </div>
            <div class="macrotheme-card">
                <div class="macrotheme-title">
                    <span class="macrotheme-icon-box" aria-hidden="true">
                        <svg class="macrotheme-icon" viewBox="0 0 24 24">
                            {% if cover.macrotema.icone == "health" %}
                            <path d="M10 5h4v5h5v4h-5v5h-4v-5H5v-4h5z" fill="currentColor"/>
                            {% elif cover.macrotema.icone == "book" %}
                            <path d="M5 5.5c2.6 0 4.5.5 7 2v11c-2.5-1.5-4.4-2-7-2zM19 5.5c-2.6 0-4.5.5-7 2v11c2.5-1.5 4.4-2 7-2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                            {% elif cover.macrotema.icone == "people" %}
                            <path d="M8.5 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM15.5 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM3.5 19c.7-3.2 2.5-5 5-5s4.3 1.8 5 5zM12.5 19c.5-2.2 1.7-3.7 3.6-3.7 2 0 3.4 1.4 4 3.7z" fill="currentColor"/>
                            {% elif cover.macrotema.icone == "drop" %}
                            <path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                            {% elif cover.macrotema.icone == "water" %}
                            <path d="M3 9c2 0 2 1.5 4 1.5S9 9 11 9s2 1.5 4 1.5S17 9 21 9M3 15c2 0 2 1.5 4 1.5S9 15 11 15s2 1.5 4 1.5S17 15 21 15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            {% else %}
                            <path d="M4 17h16M7 15l3-4 3 3 4-6 3 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            {% endif %}
                        </svg>
                    </span>
                    <span class="macrotheme-name">{{ cover.macrotema.nome }}</span>
                </div>
                <span class="macrotheme-status">{{ cover.macrotema.status }}</span>
            </div>
            <div class="macrotheme-summary">
                <h2 class="macrotheme-summary-title">Resumo</h2>
                <p class="macrotheme-summary-text">{{ cover.macrotema.resumo }}</p>
            </div>
            <div class="indicator-scores">
                <h2 class="indicator-scores-title">Scores por indicador</h2>
                <div class="indicator-score-grid">
                    {% for indicador in cover.macrotema.indicadores %}
                    <div class="indicator-score-card">
                        <svg class="indicator-icon" viewBox="0 0 24 24" aria-hidden="true">
                            {% if indicador.icone == "hospital" %}
                            <path d="M4 21V8h5V3h6v5h5v13H4zM10 7h4M12 10v7M8.5 13.5h7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            {% elif indicador.icone == "vaccine" %}
                            <path d="M7 5l12 12M14 4l6 6M4 14l6 6M9 7l8 8-5 5-8-8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            {% elif indicador.icone == "birth" %}
                            <circle cx="12" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="2"/>
                            <path d="M7 21c.6-4 2.3-6 5-6s4.4 2 5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            {% elif indicador.icone == "shield" %}
                            <path d="M12 3l7 3v5c0 4.5-2.7 8-7 10-4.3-2-7-5.5-7-10V6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                            {% elif indicador.icone == "book" %}
                            <path d="M5 5.5c2.6 0 4.5.5 7 2v11c-2.5-1.5-4.4-2-7-2zM19 5.5c-2.6 0-4.5.5-7 2v11c2.5-1.5 4.4-2 7-2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                            {% elif indicador.icone == "people" %}
                            <path d="M8.5 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM15.5 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM3.5 19c.7-3.2 2.5-5 5-5s4.3 1.8 5 5zM12.5 19c.5-2.2 1.7-3.7 3.6-3.7 2 0 3.4 1.4 4 3.7z" fill="currentColor"/>
                            {% elif indicador.icone == "drop" %}
                            <path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                            {% elif indicador.icone == "water" %}
                            <path d="M3 9c2 0 2 1.5 4 1.5S9 9 11 9s2 1.5 4 1.5S17 9 21 9M3 15c2 0 2 1.5 4 1.5S9 15 11 15s2 1.5 4 1.5S17 15 21 15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            {% else %}
                            <path d="M4 17h16M7 15l3-4 3 3 4-6 3 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            {% endif %}
                        </svg>
                        <div>
                            <div class="indicator-name">{{ indicador.nome }}</div>
                            <div class="indicator-source">{{ indicador.fonte }}</div>
                        </div>
                        <span class="indicator-badge indicator-badge-{{ indicador.classe }}">{{ indicador.score }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
    </div>
</section>
{% if cover.macrotema.descricao_paragrafos %}
<section class="theme-detail-page">
    <p class="theme-detail-kicker">Relatório V1</p>
    <div class="theme-detail-header">
        <div class="cover-brand" aria-label="Data Nordeste">
            <div class="brand-mark">
                <span class="brand-squares" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span></span>
                <span>NE</span>
            </div>
            <span class="brand-subtitle">Data Nordeste</span>
        </div>
    </div>
    <h2 class="theme-detail-title">Detalhamento do tema</h2>
    {% for paragrafo_html in cover.macrotema.descricao_html %}
    {{ paragrafo_html | safe }}
    {% endfor %}
</section>
{% endif %}
{% for linha in dados %}
<div class="doc-content">{{ docs_html | safe }}</div>
{% endfor %}
<footer class="pdf-footer">
    <span>Relatório automático do Data Nordeste</span>
    <span class="pdf-footer-page" aria-label="Número da página"></span>
</footer>
</body>
</html>
"""

def render_chart_placeholder(chart_file: str) -> str:
    return (
        '<div class="chart-block">'
        f'<img src="/output/{html_module.escape(chart_file)}" alt="Gráfico">'
        '</div>'
    )


def render_mapa_marker(contexto: dict, safe_report: str | None = None) -> str:
    contentful_url = obter_url_mapa_contentful(contexto.get("nm_mun", ""))
    if contentful_url:
        cidade_segura = html_module.escape(str(contexto.get("nm_mun", "município")))
        return (
            '<figure class="map-block map-block--region">'
            '<h2 class="region-map-title">Mapa da região</h2>'
            f'<img class="region-map-image" src="{html_module.escape(contentful_url)}" '
            f'alt="Mapa da região de {cidade_segura}">'
            '</figure>'
            '<!-- fonte: contentful -->'
        )

    mapa_file = gerar_mapa_regiao(contexto.get("nm_mun", ""), safe_report or "relatorio")
    if mapa_file:
        cidade_segura = html_module.escape(str(contexto.get("nm_mun", "município")))
        return (
            '<figure class="map-block map-block--region">'
            '<h2 class="region-map-title">Mapa da região</h2>'
            f'<img class="region-map-image" src="/output/{html_module.escape(mapa_file)}" '
            f'alt="Mapa da região de {cidade_segura}">'
            '</figure>'
            '<!-- fonte: gerado_localmente -->'
        )

    return render_mapa_geografico(contexto) + '\n<!-- fonte: svg_locator -->'


def render_descricao_tema_html(descricao_tema: str, contexto: dict, namespace: str = "demografia", safe_report: str | None = None) -> list[str]:
    partes = []
    for paragrafo in re.split(r"\n\s*\n", descricao_tema):
        paragrafo = paragrafo.strip()
        if not paragrafo:
            continue

        if paragrafo.lstrip("\ufeff").strip().lower() in {"*mapa_geografico", "mapa_geografico"}:
            partes.append(render_mapa_marker(contexto, safe_report))
        else:
            paragrafo = substituir_placeholders(paragrafo, contexto, namespace)
            partes.append(
                f'<p class="theme-detail-text">{html_module.escape(paragrafo)}</p>'
            )

    return partes


def normalizar_titulo_para_match(texto: str) -> str:
    texto = re.sub(r"^\s*\d+\s*\.?\s*", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto.casefold()


def identificar_secao_macrotema(linha: str, namespace: str) -> dict[str, object] | None:
    secao = MACROTEMA_SECOES.get(namespace)
    if not secao:
        return None

    titulo_normalizado = normalizar_titulo_para_match(linha)
    aliases = [alias.casefold() for alias in secao["aliases"]]
    if titulo_normalizado in aliases or secao["titulo"].casefold() == titulo_normalizado:
        return secao
    return None


def render_section_heading(secao: dict[str, object]) -> str:
    numero = html_module.escape(str(secao["numero"]))
    titulo = html_module.escape(str(secao["titulo"]))
    return (
        '<div class="section-heading">'
        f'<span class="section-number">{numero}</span>'
        f'<div class="section-title-wrap"><span class="section-title">{titulo}</span></div>'
        '</div>'
    )


def substituir_placeholders(texto: str, contexto: dict, namespace: str = "demografia") -> str:

    def _substituir_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)

        namespaces_validos = {
            namespace.lower(),
            "linha",
            "dados",
            "csv",
        }

        if placeholder_namespace in namespaces_validos:
            return str(contexto.get(campo, match.group(0)))

        return match.group(0)

    alias_map = {
        "city": contexto.get("nm_mun", ""),
        "year": contexto.get("ano", ""),
        "municipio": contexto.get("nm_mun", ""),
        "ano": contexto.get("ano", ""),
        "data_relatorio": contexto.get("data_relatorio", ""),
        "hora_relatorio": contexto.get("hora_relatorio", ""),
        "data_geracao": contexto.get("data_relatorio", ""),
        "hora_geracao": contexto.get("hora_relatorio", ""),
    }

    resultado = texto

    resultado = re.sub(
        r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)",
        _substituir_dolar,
        resultado,
    )

    for alias, valor in alias_map.items():
        resultado = resultado.replace(f"${alias}", str(valor))

    resultado = re.sub(
        r'\{\{\s*(\w+)\s*\}\}',
        lambda m: str(contexto.get(m.group(1), m.group(0))),
        resultado,
    )

    return resultado


def texto_para_html(
    texto: str,
    contexto: dict,
    namespace: str = "demografia",
    graficos_por_placeholder: dict[str, str] | None = None,
    componentes_html: dict[str, str] | None = None,
    safe_report: str | None = None,
) -> str:

    LEGENDAS_GRAFICOS = {
        "grafico_sexo": "População por sexo",
        "grafico_porte": "Distribuição por porte",
        "grafico_top_cidades": "Top cidades",
    }

    graficos_por_placeholder = graficos_por_placeholder or {}
    componentes_html = componentes_html or {}

    texto_renderizado = substituir_placeholders(texto, contexto, namespace)

    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]

    html_lines = []

    em_lista = False
    em_metadado_docs = False

    proximo_paragrafo_destaque = False

    figura_contador = 0

    for linha in linhas:

        linha_limpa = linha.lstrip("\ufeff").strip()

        if em_metadado_docs:
            if "@@" in linha_limpa:
                em_metadado_docs = False
            continue

        metadado_match = re.match(r"^([A-Za-z_][\w]*)\s*=", linha_limpa)
        if metadado_match:
            marcador_metadado = metadado_match.group(1).lower()
            if "@@" not in linha_limpa and marcador_metadado != "descricao_tema":
                em_metadado_docs = True
            continue

        # LINHA VAZIA
        if not linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            continue

        # MAPA GEOGRÁFICO
        if linha_limpa.lower() in {"*mapa_geografico", "mapa_geografico"}:

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            html_lines.append(render_mapa_marker(contexto, safe_report))

            continue

        # COMPONENTES
        marcador_componente = re.fullmatch(
            r"##([A-Za-z_][\w]*)",
            linha_limpa,
        )

        if marcador_componente:

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            nome_componente = marcador_componente.group(1)

            if nome_componente == "tabela_resumo":

                html_lines.append(
                    render_tabela_resumo(
                        contexto=contexto,
                        namespace=namespace,
                    )
                )

            continue

        # GRÁFICOS
        marcador_grafico = re.fullmatch(
            r"%%(\w+(?:\+\w+)*)",
            linha_limpa,
        )

        if marcador_grafico:

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            tipos = [
                tipo.strip()
                for tipo in marcador_grafico.group(1).split("+")
            ]

            figuras = []

            for tipo in tipos:

                chart_file = graficos_por_placeholder.get(tipo)

                if not chart_file:
                    continue

                figuras.append(
                    '<figure style="text-align:center; margin:0; flex:1; min-width:280px;">'
                    f'<img src="/output/{html_module.escape(chart_file)}" '
                    f'alt="{html_module.escape(tipo)}" '
                    'style="width:100%; max-width:480px; object-fit:contain;">'
                    "</figure>"
                )

            if figuras:

                figura_contador += 1

                legenda = " e ".join(
                    LEGENDAS_GRAFICOS.get(tipo, tipo)
                    for tipo in tipos
                )

                html_lines.append(
                    '<div style="display:flex; gap:24px; justify-content:center; '
                    'align-items:flex-start; margin:32px 0; flex-wrap:wrap;">'
                    + "".join(figuras)
                    + "</div>"
                )

                html_lines.append(
                    f'<p class="figure-caption">'
                    f'Figura {figura_contador} - '
                    f'{html_module.escape(legenda)}'
                    f"</p>"
                )

            continue

        # TÍTULO PRINCIPAL
        if linha_limpa.startswith("#!"):

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            titulo = linha_limpa[2:].strip()

            if titulo:
                html_lines.append(
                    f"<h1>{html_module.escape(titulo)}</h1>"
                )

            continue

        # LISTAS
        if linha_limpa.startswith(("- ", "• ", "* ")):

            if not em_lista:
                html_lines.append("<ul>")
                em_lista = True

            item = html_module.escape(
                linha_limpa[2:].strip()
            )

            html_lines.append(f"<li>{item}</li>")

            continue

        if em_lista:
            html_lines.append("</ul>")
            em_lista = False

        # SEÇÕES
        secao_macrotema = identificar_secao_macrotema(
            linha_limpa,
            namespace,
        )

        if secao_macrotema:
            proximo_paragrafo_destaque = False
            continue

        elif (
            re.match(r"^\d+\.\s+", linha_limpa)
            or linha_limpa.lower()
            in {"apresentação", "demografia"}
        ):

            html_lines.append(
                f"<h2>{html_module.escape(linha_limpa)}</h2>"
            )

            proximo_paragrafo_destaque = False

        elif re.match(
            r"^figura\s+(?:[&x]|\d+)\s*[–-]",
            linha_limpa,
            flags=re.IGNORECASE,
        ):

            legenda = re.sub(
                r"\[[A-Za-z0-9]{1,3}\]",
                "",
                linha_limpa,
            ).replace("&", "")

            html_lines.append(
                f'<p class="figure-caption">'
                f"{html_module.escape(legenda.strip())}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

        else:

            linha_limpa = re.sub(
                r"\[[A-Za-z0-9]{1,3}\]",
                "",
                linha_limpa,
            )

            classe = (
                ' class="lead"'
                if proximo_paragrafo_destaque
                else ""
            )

            html_lines.append(
                f"<p{classe}>"
                f"{html_module.escape(linha_limpa)}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

    if em_lista:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
