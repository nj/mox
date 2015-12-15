package dk.magenta.mox.spreadsheet;

import dk.magenta.mox.UploadServlet;
import dk.magenta.mox.agent.*;
import dk.magenta.mox.json.JSONObject;
import org.apache.commons.fileupload.FileItem;
import org.apache.commons.fileupload.FileUploadException;
import org.apache.log4j.Logger;

import javax.servlet.ServletException;
import javax.servlet.annotation.MultipartConfig;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.Part;
import java.io.*;
import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipException;
import java.util.zip.ZipFile;

/**
 * Created by lars on 26-11-15.
 */
@WebServlet(name = "DocumentUpload")
@MultipartConfig
public class DocumentUpload extends UploadServlet {

    private HashMap<String, SpreadsheetConverter> converterMap = new HashMap<String, SpreadsheetConverter>();
    private MessageSender moxSender;
    private Properties agentProperties;

    public void init() throws ServletException {

        ArrayList<SpreadsheetConverter> converterList = new ArrayList<SpreadsheetConverter>();
        this.agentProperties = new Properties();
        try {
            this.agentProperties.load(this.getServletContext().getResourceAsStream("/WEB-INF/agent.properties"));
        } catch (IOException e) {
            throw new ServletException("Failed to load /WEB-INF/agent.properties",e);
        }
        String queueInterface = this.getPropertyOrThrow(this.agentProperties, "amqp.interface");
        String queueName = this.getPropertyOrThrow(this.agentProperties, "amqp.queue");
        String queueUsername = this.getPropertyOrThrow(this.agentProperties, "amqp.username");
        String queuePassword = this.getPropertyOrThrow(this.agentProperties, "amqp.password");

        Map<String, ObjectType> objectTypes = ObjectType.load(this.agentProperties);

        try {
            converterList.add(new OdfConverter(objectTypes));
            converterList.add(new XlsConverter(objectTypes));
            converterList.add(new XlsxConverter(objectTypes));
        } catch (IOException e) {
            throw new ServletException("Failed converter initialization", e);
        }
        for (SpreadsheetConverter converter : converterList) {
            for (String contentType : converter.getApplicableContentTypes()) {
                this.converterMap.put(contentType, converter);
            }
        }

        try {
            this.moxSender = new MessageSender(queueUsername, queuePassword, queueInterface, null, queueName);
        } catch (IOException e) {
            throw new ServletException("Unable to connect to amqp queue '"+queueInterface+"/"+queueName+"'. Documents were not dispatched.", e);
        } catch (TimeoutException e) {
            throw new ServletException("Timeout when connecting to amqp queue '"+queueInterface+"/"+queueName+"'. Documents were not dispatched.", e);
        }
    }

    private String getPropertyOrThrow(Properties properties, String key) throws ServletException {
        String value = properties.getProperty(key);
        if (value == null) {
            throw new ServletException("Failed to get property '"+key+"' from configuration file");
        }
        return value;
    }


    Logger log = Logger.getLogger(DocumentUpload.class);

    protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {

        final String[] fileFieldNames = new String[] {"file"};

        Writer output = response.getWriter();
        this.tic();

        String authorization = request.getHeader("authorization");
        if (authorization == null) {
            authorization = request.getParameter("authtoken");
        }
        if (authorization == null) {
            output.append("No authtoken present. Sucks to be you.");
        }


        ArrayList<Future<String>> moxResponses = new ArrayList<Future<String>>();
        for (String fileFieldName : fileFieldNames) {
            Part file = request.getPart(fileFieldName);

            if (file.getName() != null) {
                SpreadsheetConverter converter = this.converterMap.get(file.getContentType());
                if (converter != null) {
                    try {
                        SpreadsheetConversion conversion = converter.convert(file.getInputStream());

                        for (String sheetName : conversion.getSheetNames()) {
                            for (String objectId : conversion.getObjectIds(sheetName)) {
                                SpreadsheetConversion.ObjectData object = conversion.getObject(sheetName, objectId);
                                ObjectType objectType = converter.getObjectType(object.getSheetName());
                                String operation = object.getOperation();
                                JSONObject data = object.convert();

                                UUID uuid = null;
                                try {
                                    UUID.fromString(object.getId());
                                } catch (IllegalArgumentException e) {}

                                Future<String> moxResponse = objectType.sendCommand(this.moxSender, operation, uuid, data, authorization);
                                moxResponses.add(moxResponse);
                            }
                        }
                    } catch (Exception e) {
                        throw new ServletException("Failed converting uploaded file", e);
                    }
                } else {
                    throw new ServletException("No SpreadsheetConverter for content type '" + file.getContentType() + "'");
                }

            }
        }

        for (Future<String> moxResponse : moxResponses) {
            String responseString = null;
            try {
                responseString = moxResponse.get(30, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                e.printStackTrace();
            } catch (ExecutionException e) {
                e.printStackTrace();
            } catch (TimeoutException e) {
                e.printStackTrace();
            }
            if (responseString != null) {
                JSONObject responseObject = new JSONObject(responseString);
                if (responseObject != null) {
                    String errorType = responseObject.optString("type");
                    if (errorType != null && errorType.equalsIgnoreCase("ExecutionException")) {
                        output.append(responseObject.optString("message", "Error"));
                    }
                }
            } else {
                output.append("response timeout\n");
            }
        }

    }

    private Date startTime;
    private void tic() {
        this.startTime = new Date();
    }
    private long toc() {
        return new Date().getTime() - this.startTime.getTime();
    }
}
