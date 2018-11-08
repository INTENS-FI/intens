package fi.vtt.intens.o4j_client.eval;

import java.util.Locale;

import com.fasterxml.jackson.annotation.JsonCreator;

public enum JobStatus {
    SCHEDULED, RUNNING, DONE, CANCELLED, FAILED, INVALID;
    
    /**
     * JSON deserialiser.
     * Any case is accepted.  Null is returned for unknown statuses.
     */
    @JsonCreator
    public static JobStatus fromString(String str) {
        try {
            return valueOf(str.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
    
    /**
     * Whether the job is scheduled or running (i.e., not finished).
     * @return
     */
    boolean isActive() {
        switch (this) {
        case SCHEDULED:
        case RUNNING:
            return true;
        default:
            return false;
        }
    }
}
