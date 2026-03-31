from isaaclab.app import AppLauncher

app_launcher = AppLauncher(headless=False)
simulation_app = app_launcher.app

import isaaclab.sim as sim_utils

BIMANUAL_USD = "/home/vision/humanoids/openarm_isaac_lab/source/openarm/openarm/tasks/manager_based/openarm_manipulation/usds/openarm_bimanual/openarm_bimanual.usd"

def main():
    sim_cfg = sim_utils.SimulationCfg(dt=0.01)
    sim = sim_utils.SimulationContext(sim_cfg)
    sim.set_camera_view([2.0, 2.0, 2.0], [0.0, 0.0, 0.5])

    cfg = sim_utils.UsdFileCfg(usd_path=BIMANUAL_USD)
    cfg.func("/World/OpenArm", cfg)

    sim.reset()
    print("Bimanual OpenArm loaded.")

    while simulation_app.is_running():
        sim.step()

if __name__ == "__main__":
    main()
    simulation_app.close()