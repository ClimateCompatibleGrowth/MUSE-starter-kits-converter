import xarray as xr

from typing import cast

from muse.production import maximum_production, register_production


@register_production
def maximum_production_share_losses(
    market: xr.Dataset, capacity: xr.DataArray, technologies: xr.Dataset, **filters
) -> xr.DataArray:
    import numpy as np
    from muse.utilities import filter_input, broadcast_techs
    from muse.commodities import is_enduse

    capa = filter_input(
        capacity, **{k: v for k, v in filters.items() if k in capacity.dims}
    )

    btechs = broadcast_techs(  # type: ignore
        cast(xr.Dataset, technologies[["fixed_outputs", "utilization_factor"]]), capa
    )
    ftechs = filter_input(
        btechs, **{k: v for k, v in filters.items() if k in btechs.dims}
    )

    production = capa * ftechs.fixed_outputs * ftechs.utilization_factor

    print("capa: \n{}".format(capa))
    print("ftechs: \n{}".format(ftechs))
    print("production: \n{}".format(production))
    # print("market.electricity: \n{}".format(market.sel(commodity="electricity")))

    constraints = {
        "Solar PV (Utility)": 0.15,
        "Offshore Wind": 0.1,
        "Onshore Wind": 0.25,
        "Biomass Power Plant": 0.3,
    }

    max_production = production
    for string in constraints:

        index = (
            (max_production.technology == string)
            & (max_production.commodity == "electricity")
            & (max_production >= constraints[string])
        )

        production_limit = constraints[string] * market.sum()
        print("max_production 1: \n{}".format(max_production))
        max_production = max_production.where(~index, constraints[string])
        print("max_production.where(index) 2: \n{}".format(max_production.where(index)))
        production = production.where(
            index & (production > production_limit), max_production.where(index).values,
        )
        print("production: \n{}".format(production))
    result = production
    print("result: \n{}".format(result))
    # index = (
    #     (max_production.technology == "Solar PV (Utility)")
    #     | (max_production.technology == "Offshore Wind")
    #     | (max_production.technology == "Onshore Wind")
    #     | (max_production.technology == "Biomass Power Plant")
    #     & (max_production.commodity == "electricity")
    # )

    # print("index: \n{}".format(index))
    # result = max_production.where(~index, max_production * production)
    # print("result: \n{}".format(result))

    return result1.where(is_enduse(result.comm_usage), 0)
    # print(
    #     "max_production.sel(commodity= {}".format(
    #         max_production.sel(commodity="electricity")
    #         .where(
    #             max_production.sel(commodity="electricity").technology
    #             == "Solar PV (Utility)",
    #             drop=True,
    #         )
    #         .squeeze()
    #         .transpose("timeslice", "year"),
    #     )
    # )

    # print(
    #     "max_share.sel(commodity= {}".format(
    #         max_share.sel(commodity="electricity").sel(region="Kenya")
    #     )
    # )

    # maximum_produced = np.clip(
    #     a=max_production.sel(commodity="electricity")
    #     .where(
    #         max_production.sel(commodity="electricity").technology
    #         == "Solar PV (Utility)",
    #         drop=True,
    #     )
    #     .squeeze()
    #     .transpose("timeslice", "year"),
    #     a_min=None,
    #     a_max=max_share.sel(commodity="electricity").sel(region="Kenya"),
    # )

    # print("maximum_produced: \n{}".format(maximum_produced))

    # # mask = (maximum_production.coords["commodity"] == "electricity") & (
    # #     maximum_production.coords["technology"] == "Solar PV (Utility)"
    # # )

    # max_production = max_production.set_index(technology="technology")
    # print("max_production: \n{}".format(max_production))
    # max_production.loc[
    #     dict(commodity="electricity", technology="Solar PV (Utility)")
    # ] = maximum_produced
    # # max_production.where(
    # #     (max_production.commodity == "electricity")
    # #     & (max_production.technology == "Solar PV (Utility)")
    # # )  # = maximum_produced

    # # max_production(mask) = max_production.where(mask, maximum_produced, max_production(mask))
    # result = max_production
    # print("result \n{}".format(result))
