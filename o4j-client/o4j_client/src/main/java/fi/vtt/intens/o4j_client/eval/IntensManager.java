package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.InputStream;

import eu.cityopt.sim.eval.ConfigurationException;
import eu.cityopt.sim.eval.Namespace;
import eu.cityopt.sim.eval.SimulationModel;
import eu.cityopt.sim.eval.SimulationRunner;
import eu.cityopt.sim.eval.SimulatorManager;


/**
 * A factory for simulations that execute on simsvc.
 * @author ttekth
 *
 */
public class IntensManager implements SimulatorManager {

	public void close() throws IOException {
		// TODO Auto-generated method stub

	}

	public SimulationModel parseModel(String simulatorName, InputStream modelData)
			throws IOException, ConfigurationException {
		// TODO Auto-generated method stub
		return null;
	}

	public SimulationRunner makeRunner(SimulationModel model, Namespace namespace)
			throws IOException, ConfigurationException {
		// TODO Auto-generated method stub
		return null;
	}

}
