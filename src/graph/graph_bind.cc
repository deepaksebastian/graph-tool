// graph-tool -- a general graph modification and manipulation thingy
//
// Copyright (C) 2007-2011 Tiago de Paula Peixoto <tiago@skewed.de>
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 3
// of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <http://www.gnu.org/licenses/>.

#include <boost/python.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>

#define NUMPY_EXPORT
#include "numpy_bind.hh"

#include "graph.hh"
#include "graph_python_interface.hh"
#include "graph_util.hh"

#ifdef HAVE_SCIPY // integration with scipy weave
#include "weave/scxx/object.h"
#include "weave/scxx/list.h"
#include "weave/scxx/tuple.h"
#include "weave/scxx/dict.h"
#include "weave/scxx/str.h"
#endif

using namespace std;
using namespace graph_tool;
using namespace boost;
using namespace boost::python;

struct LibInfo
{
    string GetName()      const {return PACKAGE_NAME;}
    string GetAuthor()    const {return AUTHOR;}
    string GetCopyright() const {return COPYRIGHT;}
    string GetVersion()   const {return VERSION " (commit " GIT_COMMIT
                                        ", " GIT_COMMIT_DATE ")";}
    string GetLicense()   const {return "GPL version 3 or above";}
    string GetCXXFLAGS()  const {return CPPFLAGS " " CXXFLAGS " " LDFLAGS;}
    string GetInstallPrefix() const {return INSTALL_PREFIX;}
    string GetPythonDir() const {return PYTHON_DIR;}
    string GetGCCVersion() const
    {
        stringstream s;
        s << __GNUC__ << "." << __GNUC_MINOR__ << "." <<  __GNUC_PATCHLEVEL__;
        return s.str();
    }
};

template <class ValueType>
struct vector_from_list
{
    vector_from_list()
    {
        converter::registry::push_back
            (&convertible, &construct,
             boost::python::type_id<vector<ValueType> >());
    }

    static void* convertible(PyObject* obj_ptr)
    {
        handle<> x(borrowed(obj_ptr));
        object o(x);
        size_t N = len(o);
        for (size_t i = 0; i < N; ++i)
        {
            extract<ValueType> elem(o[i]);
            if (!elem.check())
                return 0;
        }
        return obj_ptr;
    }

    static void construct(PyObject* obj_ptr,
                          converter::rvalue_from_python_stage1_data* data)
    {
        handle<> x(borrowed(obj_ptr));
        object o(x);
        vector<ValueType> value;
        size_t N = len(o);
        for (size_t i = 0; i < N; ++i)
            value.push_back(extract<ValueType>(o[i]));
        void* storage =
            ( (boost::python::converter::rvalue_from_python_storage
               <vector<ValueType> >*) data)->storage.bytes;
        new (storage) vector<ValueType>(value);
        data->convertible = storage;
    }
};

template <class ValueType>
bool vector_equal_compare(const vector<ValueType>& v1,
                          const vector<ValueType>& v2)
{
    if (v1.size() != v2.size())
        return false;
    for (size_t i = 0; i < v1.size(); ++i)
    {
        if (v1[i] != v2[i])
            return false;
    }
    return true;
}

template <class ValueType>
bool vector_nequal_compare(const vector<ValueType>& v1,
                           const vector<ValueType>& v2)
{
    return !vector_equal_compare(v1,v2);
}

struct export_vector_types
{
    template <class ValueType>
    void operator()(ValueType) const
    {
        string type_name = get_type_name<>()(typeid(ValueType));
        if (type_name == "long double")
            type_name = "long_double";
        string name = "Vector_" + type_name;
        class_<vector<ValueType> > vc(name.c_str());
        vc.def(vector_indexing_suite<vector<ValueType> >())
            .def("__eq__", &vector_equal_compare<ValueType>)
            .def("__ne__", &vector_nequal_compare<ValueType>);
        wrap_array(vc, typename mpl::has_key<numpy_types,ValueType>::type());
        vector_from_list<ValueType>();
    }

    template <class ValueType>
    void wrap_array(class_<vector<ValueType> >& vc, mpl::true_) const
    {
        vc.def("get_array", &wrap_vector_not_owned<ValueType>);
    }

    template <class ValueType>
    void wrap_array(class_<vector<ValueType> >& vc, mpl::false_) const
    {
    }
};

// exception translation
template <class Exception>
void graph_exception_translator(const Exception& e)
{
    PyObject* error;
    if (is_same<Exception, GraphException>::value)
        error = PyExc_RuntimeError;
    if (is_same<Exception, IOException>::value)
        error = PyExc_IOError;
    if (is_same<Exception, ValueException>::value)
        error = PyExc_ValueError;

    PyObject* message = PyString_FromString(e.what());
    PyObject_SetAttrString(error, "message", message);
    PyErr_SetString(error, e.what());
}

void raise_error(const string& msg)
{
    throw GraphException(msg);
}

template <class T1, class T2>
struct pair_to_tuple
{
    static PyObject* convert(const pair<T1,T2>& p)
    {
        boost::python::tuple t = boost::python::make_tuple(p.first,p.second);
        return incref(t.ptr());
    }
};

template <class T1, class T2>
struct pair_from_tuple
{
    pair_from_tuple()
    {
        converter::registry::push_back(&convertible, &construct,
                                       boost::python::type_id<pair<T1,T2> >());
    }

    static void* convertible(PyObject* obj_ptr)
    {
        handle<> x(borrowed(obj_ptr));
        object o(x);
        extract<T1> first(o[0]);
        extract<T2> second(o[1]);
        if (!first.check() || !second.check())
            return 0;
        return obj_ptr;
    }

    static void construct(PyObject* obj_ptr,
                          converter::rvalue_from_python_stage1_data* data)
    {
        handle<> x(borrowed(obj_ptr));
        object o(x);
        pair<T1,T2> value;
        value.first = extract<T1>(o[0]);
        value.second = extract<T2>(o[1]);
        void* storage =
            ( (boost::python::converter::rvalue_from_python_storage
               <pair<T1,T2> >*) data)->storage.bytes;
        new (storage) pair<T1,T2>(value);
        data->convertible = storage;
    }
};

template <class ValueType>
struct variant_from_python
{
    variant_from_python()
    {
        converter::registry::push_back
            (&convertible, &construct,
             boost::python::type_id<GraphInterface::deg_t>());
    }

    static void* convertible(PyObject* obj_ptr)
    {
        handle<> x(borrowed(obj_ptr));
        object o(x);
        extract<ValueType> str(o);
        if (!str.check())
            return 0;
        return obj_ptr;
    }

    static void construct(PyObject* obj_ptr,
                          converter::rvalue_from_python_stage1_data* data)
    {
        handle<> x(borrowed(obj_ptr));
        object o(x);
        ValueType value = extract<ValueType>(o);
        GraphInterface::deg_t deg = value;
        void* storage =
            ( (boost::python::converter::rvalue_from_python_storage
               <GraphInterface::deg_t>*) data)->storage.bytes;
        new (storage) GraphInterface::deg_t(deg);
        data->convertible = storage;
    }
};

// scipy weave integration
#ifdef HAVE_SCIPY
template <class ScxxType>
struct scxx_to_python
{
    static PyObject* convert(const ScxxType& o)
    {
        return incref((PyObject*)(o));
    }
};
#endif

// persistent python object IO
namespace graph_tool
{
extern python::object object_pickler;
extern python::object object_unpickler;
}

void set_pickler(python::object o)
{
    graph_tool::object_pickler = o;
}

void set_unpickler(python::object o)
{
    graph_tool::object_unpickler = o;
}

python::list get_property_types()
{
    python::list plist;
    for (int i = 0; i < mpl::size<value_types>::value; ++i)
        plist.append(string(type_names[i]));
    return plist;
}

struct graph_type_name
{
    template <class Graph>
    void operator()(const Graph& g, string& name) const
    {
        using python::detail::gcc_demangle;
        name = string(gcc_demangle(typeid(Graph).name()));
    }
};

string get_graph_type(GraphInterface& g)
{
    string name;
    run_action<>()(g, bind<void>(graph_type_name(), _1, ref(name)))();
    return name;
}

bool openmp_enabled()
{
#ifdef USING_OPENMP
    return true;
#else
    return false;
#endif
}

void ungroup_vector_property(GraphInterface& g, boost::any vector_prop,
                             boost::any prop, size_t pos, bool edge);
void group_vector_property(GraphInterface& g, boost::any vector_prop,
                           boost::any prop, size_t pos, bool edge);
void export_python_interface();

BOOST_PYTHON_MODULE(libgraph_tool_core)
{
    // numpy
    import_array();

    export_python_interface();

    register_exception_translator<GraphException>
        (graph_exception_translator<GraphException>);
    register_exception_translator<IOException>
        (graph_exception_translator<IOException>);
    register_exception_translator<ValueException>
        (graph_exception_translator<ValueException>);

    def("raise_error", &raise_error);
    def("get_property_types", &get_property_types);
    class_<boost::any>("any");

    def("graph_filtering_enabled", &graph_filtering_enabled);
    def("openmp_enabled", &openmp_enabled);

    mpl::for_each<mpl::push_back<scalar_types,string>::type>(export_vector_types());

    class_<GraphInterface>("GraphInterface", init<>())
        .def(init<GraphInterface,bool>())
        .def("GetNumberOfVertices", &GraphInterface::GetNumberOfVertices)
        .def("GetNumberOfEdges", &GraphInterface::GetNumberOfEdges)
        .def("SetDirected", &GraphInterface::SetDirected)
        .def("GetDirected", &GraphInterface::GetDirected)
        .def("SetReversed", &GraphInterface::SetReversed)
        .def("GetReversed", &GraphInterface::GetReversed)
        .def("SetVertexFilterProperty",
             &GraphInterface::SetVertexFilterProperty)
        .def("IsVertexFilterActive", &GraphInterface::IsVertexFilterActive)
        .def("SetEdgeFilterProperty",
             &GraphInterface::SetEdgeFilterProperty)
        .def("IsEdgeFilterActive", &GraphInterface::IsEdgeFilterActive)
        .def("PurgeVertices",  &GraphInterface::PurgeVertices)
        .def("PurgeEdges",  &GraphInterface::PurgeEdges)
        .def("ShiftVertexProperty",  &GraphInterface::ShiftVertexProperty)
        .def("WriteToFile", &GraphInterface::WriteToFile)
        .def("ReadFromFile",&GraphInterface::ReadFromFile)
        .def("DegreeMap", &GraphInterface::DegreeMap)
        .def("Clear", &GraphInterface::Clear)
        .def("ClearEdges", &GraphInterface::ClearEdges)
        .def("GetVertexIndex", &GraphInterface::GetVertexIndex)
        .def("GetEdgeIndex", &GraphInterface::GetEdgeIndex)
        .def("GetMaxEdgeIndex", &GraphInterface::GetMaxEdgeIndex)
        .def("ReIndexEdges", &GraphInterface::ReIndexEdges)
        .def("GetGraphIndex", &GraphInterface::GetGraphIndex)
        .def("CopyVertexProperty", &GraphInterface::CopyVertexProperty)
        .def("CopyEdgeProperty", &GraphInterface::CopyEdgeProperty);

    class_<GraphInterface::vertex_index_map_t>("vertex_index_map", no_init);
    class_<GraphInterface::edge_index_map_t>("edge_index_map", no_init);
    class_<GraphInterface::graph_index_map_t>("graph_index_map", no_init);

    enum_<GraphInterface::degree_t>("Degree")
        .value("In", GraphInterface::IN_DEGREE)
        .value("Out", GraphInterface::OUT_DEGREE)
        .value("Total", GraphInterface::TOTAL_DEGREE);

    variant_from_python<boost::any>();
    variant_from_python<GraphInterface::degree_t>();
    to_python_converter<pair<string,bool>, pair_to_tuple<string,bool> >();
    to_python_converter<pair<size_t,size_t>, pair_to_tuple<size_t,size_t> >();
    to_python_converter<pair<double,double>, pair_to_tuple<double,double> >();
    pair_from_tuple<double,double>();
    pair_from_tuple<size_t,size_t>();
#ifdef HAVE_SCIPY
    to_python_converter<py::object, scxx_to_python<py::object> >();
    to_python_converter<py::tuple, scxx_to_python<py::tuple> >();
    to_python_converter<py::list, scxx_to_python<py::list> >();
    to_python_converter<py::dict, scxx_to_python<py::dict> >();
    to_python_converter<py::str, scxx_to_python<py::str> >();
#endif

    class_<IStream>("IStream", no_init).def("Read", &IStream::Read);
    class_<OStream>("OStream", no_init).def("Write", &OStream::Write).
        def("Flush", &OStream::Flush);
    def("set_pickler", &set_pickler);
    def("set_unpickler", &set_unpickler);

    def("group_vector_property", &group_vector_property);
    def("ungroup_vector_property", &ungroup_vector_property);

    class_<LibInfo>("mod_info")
        .add_property("name", &LibInfo::GetName)
        .add_property("author", &LibInfo::GetAuthor)
        .add_property("copyright", &LibInfo::GetCopyright)
        .add_property("version", &LibInfo::GetVersion)
        .add_property("license", &LibInfo::GetLicense)
        .add_property("cxxflags", &LibInfo::GetCXXFLAGS)
        .add_property("install_prefix", &LibInfo::GetInstallPrefix)
        .add_property("python_dir", &LibInfo::GetPythonDir)
        .add_property("gcc_version", &LibInfo::GetGCCVersion);

    def("get_graph_type", &get_graph_type);
}

