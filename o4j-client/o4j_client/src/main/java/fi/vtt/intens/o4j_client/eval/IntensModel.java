package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.Writer;
import java.time.Duration;
import java.util.List;
import java.util.Locale.LanguageRange;
import java.util.Map;

import eu.cityopt.sim.eval.Namespace;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationModel;
import eu.cityopt.sim.eval.SimulatorManager;

public class IntensModel implements SimulationModel {

	public void close() throws IOException {
		// TODO Auto-generated method stub

	}

	public SimulatorManager getSimulatorManager() {
		// TODO Auto-generated method stub
		return null;
	}

	public String getSimulatorName() {
		// TODO Auto-generated method stub
		return null;
	}

	public Defaults getDefaults() {
		// TODO Auto-generated method stub
		return null;
	}

	public Duration getNominalSimulationRuntime() {
		// TODO Auto-generated method stub
		return null;
	}

	public String getDescription(List<LanguageRange> priorityList) {
		// TODO Auto-generated method stub
		return null;
	}

	public byte[] getOverviewImageData() {
		// TODO Auto-generated method stub
		return null;
	}

	public SimulationInput findInputsAndOutputs(Namespace newNamespace, Map<String, Map<String, String>> units,
			int detailLevel, Writer warningWriter) throws IOException {
		// TODO Auto-generated method stub
		return null;
	}

}
