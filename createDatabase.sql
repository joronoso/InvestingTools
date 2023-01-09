drop table xbrl_dimension;
drop table xbrl_fact;
drop table xbrl_document;
drop table xbrl_company;
drop table xbrl_period_instant;


CREATE TABLE "xbrl_period_instant" (
	[id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	[start_date] TEXT NOT NULL,
	[end_date] TEXT
);
-- Vamos a usar la misma tabla para almacenar periodos en instantes. Los instantes dejarán end_date a NULL.
-- Mi idea ahora mismo es hacer una lista unica de periodos, que no vayan asociados a ningun documento concreto. Cada documento que se inserte tendra que ver si el periodo que quiere usa ya existe y apuntar a ese. Creo que facilitara la comparabilidad, aunque hay que tener cuidado al hacer las inserciones.


CREATE TABLE "xbrl_fact" (
	[id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	[company_id] INTEGER,
	[document_id] INTEGER,
	[period_instant_id] INTEGER,
	[namespace] TEXT,
	[name] TEXT NOT NULL,
	[unit] TEXT,
	[scale] INTEGER,
	[format] TEXT, 
	[value] TEXT,
	FOREIGN KEY ([company_id]) REFERENCES "xbrl_company" ([id])
	FOREIGN KEY ([document_id]) REFERENCES "xbrl_document" ([id])
	FOREIGN KEY ([period_instant_id]) REFERENCES "xbrl_period_instant" ([id])
);

CREATE TABLE "xbrl_company" (
	[id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	[sec_id] TEXT,
	[name] TEXT,
	[ticker] TEXT
);

CREATE TABLE "xbrl_document" (
	[id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	[url] TEXT,
	[company_id] INTEGER,
	[doctype] TEXT, -- 10-K, 10-Q, ...
	[year] TEXT,
	[period] TEXT, -- FY, Q1, Q2, ...
	FOREIGN KEY ([company_id]) REFERENCES "xbrl_company" ([id])
);

CREATE TABLE "xbrl_dimension" (
	[id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	[fact_id] INTEGER NOT NULL,
	[dim_namespace] TEXT,
	[dimension] TEXT,
	[value] TEXT,
	FOREIGN KEY ([fact_id]) REFERENCES "xbrl_fact" ([id])
);

-- The following ones could very well be a different database. 
-- They are to store the information for training the valuing model.

CREATE TABLE "data_10k" (
	[cik] TEXT not null,
	[ticker] TEXT,
	[accessionNumber] TEXT not null,
	[filing_url] TEXT,
	[filing_date] TEXT,
	[end_period_date] TEXT,
	[Revenues] INTEGER,
	[OperatingIncome] INTEGER,
	[NetIncome] INTEGER,
	[Taxes] INTEGER,
	[Interest] INTEGER,
	[EBIT] INTEGER,
	[Assets] INTEGER,
	[Liabilities] INTEGER,
	[CurrentLiabilities] INTEGER,
	[AFCF] INTEGER,
	[cwc] INTEGER,
	[ROE] REAL,
	[ROA] REAL,
	[ROCE] REAL,
	[OperatingMargin] REAL,
	[InterestCoverageRatio] REAL,
	[PriceToAFCF] REAL,
	[DebtToEquity] REAL,
	[market_cap] INTEGER,
	[market_cap_date] TEXT,
	[create_timestamp] TEXT not null,
	[fixed] INTEGER, --1 if fixed
	[comment] TEXT,
	PRIMARY KEY ([cik], [accessionNumber])
);


CREATE TABLE "pending_data" (
	[cik] TEXT not null,
	[ticker] TEXT,
	[accessionNumber] TEXT not null,
	[filingDate] TEXT,
	[reportDate] TEXT,
	[filingUrl] TEXT,
	PRIMARY KEY ([cik], [accessionNumber])
);

CREATE TABLE "company_details" (
	[cik] TEXT not null,
	[name] TEXT,
	[ticker] TEXT,
	[sic] TEXT,
	[exclude] INTEGER, -- 1 to exclude
	[exclude_comments] TEXT,
	[polygon_ticker] TEXT
	PRIMARY KEY ([cik])
);

create TABLE "sic_codes" (
	[sic] TEXT not null,
	[office] TEXT,
	[description] TEXT,
	PRIMARY KEY ([sic])
);


-- This I'm thinking of creating in a separate database, mainly for concerns about making the database file too big.
-- The idea here is to store the calculations based on the result of the training.
CREATE TABLE "valuations" (
	[cik] TEXT not null,
	[ticker] TEXT,
	[end_period_date] TEXT,
	[Revenues] INTEGER,
	[OperatingIncome] INTEGER,
	[NetIncome] INTEGER,
	[Taxes] INTEGER,
	[Interest] INTEGER,
	[EBIT] INTEGER,
	[Assets] INTEGER,
	[Liabilities] INTEGER,
	[CurrentLiabilities] INTEGER,
	[AFCF] INTEGER,
	[cwc] INTEGER,
	[ROE] REAL,
	[ROA] REAL,
	[ROCE] REAL,
	[OperatingMargin] REAL,
	[InterestCoverageRatio] REAL,
	[DebtToEquity] REAL,
	[market_cap] INTEGER,
	[PriceToAFCF_actual] REAL,
	[PriceToAFCF_predicted] REAL,
	[market_cap_date] TEXT,
	[metrics_date] TEXT not null,
	[prediction_date] TEXT,
	PRIMARY KEY ([cik], [end_period_date])
);


