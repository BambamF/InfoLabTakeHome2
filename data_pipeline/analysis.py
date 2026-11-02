

def print_analysis(readings, sites):

    print("\n" + "=" * 55)
    print("LONDON AIR QUALITY DATASET ANALYSIS")
    print("=" * 55)

    print(f"\nTotal monitoring sites: {sites['site_code'].nunique()}")
    print(f"Total readings: {len(readings)}")

    if readings.empty:
        print("\nNo readings available for analysis.")
        return

    print(
        f"Date range: "
        f"{readings['recorded_at'].min().date()} "
        f"to "
        f"{readings['recorded_at'].max().date()}"
    )

    print(
        f"Unique boroughs: "
        f"{readings['borough'].nunique()}"
    )

    print(
        f"Unique pollutants: "
        f"{readings['pollutant'].nunique()}"
    )

    print("\n--- Pollutant distribution ---")

    print(
        readings.groupby("pollutant")
        .agg(
            readings=("air_quality_index", "count"),
            average_index=("air_quality_index", "mean"),
            maximum_index=("air_quality_index", "max")
        )
        .round(2)
        .to_string()
    )

    print("\n--- Borough comparison ---")

    borough_summary = (
        readings.groupby("borough")
        .agg(
            sites=("site_code", "nunique"),
            readings=("air_quality_index", "count"),
            average_index=("air_quality_index", "mean"),
            maximum_index=("air_quality_index", "max")
        )
        .round(2)
        .sort_values("maximum_index", ascending=False)
    )

    print(borough_summary.to_string())

    print("\n--- Data quality ---")

    print(
        "Missing air quality indexes:",
        readings["air_quality_index"].isna().sum()
    )

    print(
        "Duplicate readings:",
        readings.duplicated(
            subset=["site_code", "pollutant", "recorded_at"]
        ).sum()
    )

    print("=" * 55 + "\n")