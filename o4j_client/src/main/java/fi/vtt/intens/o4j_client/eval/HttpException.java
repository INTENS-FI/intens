package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;

/**
 * An exception class for HTTP errors.
 */
public class HttpException extends IOException {
    private static final long serialVersionUID = 1L;
    
    public Integer httpStatus;

    public HttpException() {}
    
    public HttpException(int status, String message) {
        super(message);
        httpStatus = status;
    }

    public HttpException(Throwable cause) {
        super(cause);
    }

    public HttpException(int status, String message, Throwable cause) {
        super(message, cause);
        httpStatus = status;
    }

    @Override
    public String getMessage() {
        var msg = super.getMessage();
        if (httpStatus != null)
            msg += "\nHTTP status code: " + httpStatus;
        return msg;
    }
}
