/*
Copyright (C) 2015-2019 Magenta ApS, https://magenta.dk.
Contact: info@magenta.dk.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/


package dk.magenta.mox.agent.exceptions;

/**
 * Created by lars on 06-10-15.
 */
public class InvalidOperationException extends Exception {
    public InvalidOperationException(String operation) {
        super("Operation '"+operation+"' does not exist.");
    }
}
