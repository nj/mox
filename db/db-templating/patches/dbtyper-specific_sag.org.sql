-- Copyright (C) 2015 Magenta ApS, http://magenta.dk.
-- Contact: info@magenta.dk.
--
-- This Source Code Form is subject to the terms of the Mozilla Public
-- License, v. 2.0. If a copy of the MPL was not distributed with this
-- file, You can obtain one at http://mozilla.org/MPL/2.0/.

/*
NOTICE: This file is auto-generated using the script: apply-template.py sag dbtyper-specific.jinja.sql
*/

--create custom type sans db-ids to be able to do "clean" function signatures "for the outside world".

CREATE TYPE SagFremdriftTils AS ENUM ('Opstaaet','Oplyst','Afgjort','Bestilt','Udfoert','Afsluttet',''); --'' means undefined (which is needed to clear previous defined tilstand_values in an already registered virksnings-periode)

CREATE TYPE SagFremdriftTilsType AS (
    virkning Virkning,
    fremdrift SagFremdriftTils
)
;

CREATE TYPE SagEgenskaberAttrType AS (
brugervendtnoegle text, 
afleveret boolean,
beskrivelse text,
hjemmel text,
kassationskode text, 
offentlighedundtaget offentlighedundtagetType, 
principiel boolean,
sagsnummer text,
titel text,
 virkning Virkning
);


CREATE TYPE SagRelationKode AS ENUM  ('behandlingarkiv','afleveringsarkiv','primaerklasse','opgaveklasse','handlingsklasse','kontoklasse','sikkerhedsklasse','foelsomhedsklasse','indsatsklasse','ydelsesklasse','ejer','ansvarlig','primaerbehandler','udlaanttil','primaerpart','ydelsesmodtager','oversag','praecedens','afgiftsobjekt','ejendomsskat','andetarkiv','andrebehandlere','sekundaerpart','andresager','byggeri','fredning','journalpost');  --WARNING: Changes to enum names requires MANUALLY rebuilding indexes where _as_convert_sag_relation_kode_to_txt is invoked.
CREATE TYPE SagRelationJournalPostSpecifikKode AS ENUM ('journalnotat','vedlagtdokument','tilakteretdokument');

CREATE TYPE JournalNotatType AS (
titel text,
notat text,
format text
);

CREATE TYPE JournalPostDokumentAttrType AS (
dokumenttitel text,
offentlighedUndtaget OffentlighedundtagetType
);


CREATE TYPE SagRelationType AS (
  relType SagRelationKode,
  virkning Virkning,
  relMaalUuid uuid,
  relMaalUrn  text,
  objektType text,
  relIndex int,
  relTypeSpec SagRelationJournalPostSpecifikKode,
  journalNotat JournalNotatType,
  journalDokumentAttr JournalPostDokumentAttrType
)
;


--we create custom cast function to json for SagRelationType, which will be invoked by custom cast to json form SagType
CREATE OR REPLACE FUNCTION actual_state._sag_relation_type_to_json(SagRelationType) 

RETURNS
json
AS 
$$
DECLARE 
result json;
keys_to_delete text[];
BEGIN

IF $1.relindex IS NULL THEN
  keys_to_delete:=array_append(keys_to_delete,'relindex');
END IF;

IF $1.reltypespec IS NULL THEN
  keys_to_delete:=array_append(keys_to_delete,'reltypespec');
END IF;

IF $1.journalnotat IS NULL OR ( ($1.journalnotat).titel IS NULL AND ($1.journalnotat).notat IS NULL AND ($1.journalnotat).format IS NULL) THEN
  keys_to_delete:=array_append(keys_to_delete,'journalnotat');
END IF;

IF $1.journaldokumentattr IS NULL 
    OR ( 
        ($1.journaldokumentattr).dokumenttitel IS NULL 
        AND 
        (
          ($1.journaldokumentattr).offentlighedundtaget IS NULL 
          OR
          (
            (($1.journaldokumentattr).offentlighedundtaget).alternativtitel IS NULL
            AND 
             (($1.journaldokumentattr).offentlighedundtaget).hjemmel IS NULL  
          )
        )
      ) THEN
    keys_to_delete:=array_append(keys_to_delete,'journaldokumentattr');
END IF;    

SELECT actual_state._json_object_delete_keys(row_to_json($1),keys_to_delete) into result;

RETURN result;

END;
$$ LANGUAGE plpgsql immutable;

create cast (SagRelationType as json) with function _sag_relation_type_to_json (SagRelationType); 


CREATE TYPE SagRegistreringType AS
(
registrering RegistreringBase,
tilsFremdrift SagFremdriftTilsType[],
attrEgenskaber SagEgenskaberAttrType[],
relationer SagRelationType[]
);

CREATE TYPE SagType AS
(
  id uuid,
  registrering SagRegistreringType[]
);  

CREATE Type _SagRelationMaxIndex AS
(
  relType SagRelationKode,
  relIndex int
);

