from bokeh.models import Transform, CustomJSTransform, CustomJSFilter
from bokeh.transform import transform

JSBoolToStr=lambda: CustomJSTransform(
    v_func="return xs.map(x => (x==true ? 'True' : (x==false ? 'False': 'None')));")
JSIntToStr=lambda: CustomJSTransform(
    v_func="return xs.map(x => String(x));")
JSRoundedFloatToStr=lambda dig: CustomJSTransform(args={'dig':dig},
    v_func="let ys; ys= xs.map(x => x.toFixed(dig));  return ys;")

MultiAbsTransform=lambda: CustomJSTransform(v_func="return xs.map(x=>(x.map(Math.abs)));")
multi_abs_transform=lambda field: transform(field,MultiAbsTransform())

JSGroupFilter=lambda field,group: CustomJSFilter(args={'field':field,'group':group},
     code="if(!(field in source.data)) {console.error('Trying to filter on non-existent field: '+field); return [];}" \
          "return source.data[field].map((x)=>(x==group));")

MultiNormalizeAndShiftTransform=lambda source, norm, shift, by_division=True, and_abs=False: \
    CustomJSTransform(args={'source': source,'norm_field': norm,'shift_field': shift},
                      v_func="""
            let shift,norm;
            if (!xs) {return null;}
            window.xs=xs
            if (typeof shift_field === 'string' || shift_field instanceof String) {
                if (!(shift_field in source.data)) alert(shift_field+" not in source.data");
                shift=source.data[shift_field];
            }
            else {
                //console.log("Making shift");
                shift=Array(xs.length).fill(shift_field);
            }
            if (typeof norm_field === 'string' || norm_field instanceof String) {
                if (!(norm_field in source.data)) alert(norm_field+" not in source.data");
                norm= source.data[norm_field];
            }
            else {
                //console.log("Making norm");
                norm=Array(xs.length).fill(norm_field);
            }
            let ys=[];
            for (let i=0; i<xs.length; i++){
                ys.push(xs[i].map(xi=>$$ABS$$((xi-shift[i])$$OP$$norm[i])));
            }
            //console.log("Returning");
            return ys;
            """.replace("$$OP$$",('/' if by_division else '*')).replace("$$ABS$$",('Math.abs' if and_abs else ''))
                      )
multi_normalize_transform=lambda field, norm, source=None, by_division=True, and_abs=False: \
    transform(field,MultiNormalizeAndShiftTransform(source=source,norm=norm,shift=0,
                                                    by_division=by_division,and_abs=and_abs))


ScalarNormalizeAndShiftTransform=lambda source, norm, shift: \
    CustomJSTransform(args={'source': source,'norm_field': norm,'shift_field': shift},
                      v_func="""
            let shift,norm;
            if (typeof shift_field === 'string' || shift_field instanceof String) {
                if (!(shift_field in source.data)) alert(shift_field+" not in source.data");
                shift=source.data[shift_field];
            }
            else {
                shift=Array(source.length).fill(shift_field);
            }
            if (typeof norm_field === 'string' || norm_field instanceof String) {
                if (!(norm_field in source.data)) alert(norm_field+" not in source.data");
                norm= source.data[norm_field];
            }
            else {
                norm=Array(source.length).fill(norm_field);
            }
            let ys=[];
            for (let i=0; i<source.length; i++){
                ys.push((xs[i]-shift[i])/norm[i]);
            }
            return ys;
            """
                      )

def compose_transforms(*transforms: Transform) -> CustomJSTransform:
    """ Creates a CustomJSTranform that is the product of the transforms.

    Ordering: "first transform supplied is first transform applied."

    Credit for this approach goes to MHankin and N.C. van Gilse on this StackOverflow page
        https://stackoverflow.com/questions/48772907/layering-or-nesting-multiple-bokeh-transforms

    Example call:

        fig=figure(width=300,height=300,toolbar_location=None)
        cds=ColumnDataSource({'x':np.arange(6.0),'y':np.arange(6.0)})

        # Produce a square root line with a single transform
        trans=CustomJSTransform(v_func="return xs.map(x=>x**.5)")
        fig.line(x='x',y=transform('y',trans),source=cds)

        # Produce a squared line with a trivial composite of a single transform
        trans=CompositeTransform(
            CustomJSTransform(v_func="return xs.map(x=>x**2)"))
        fig.line(x='x',y=transform('y',trans),source=cds)

        # Produce a straight line with a composite of a two transforms
        trans=CompositeTransform(
            CustomJSTransform(v_func="return xs.map(x=>x**2)"),
            CustomJSTransform(v_func="return xs.map(x=>x**.5)"))
        fig.line(x='x',y=transform('y',trans),source=cds)

        show(fig)

    """
    composite_transform_func = """
      let res = x;
      for (let i = 0; i < tlist.length; i++) {
        let trans = eval(tlist[i]);
        res = trans.compute(res)
      }
      return res
    """

    composite_transform_v_func = """
      let res = xs;
      for (let i = 0; i < tlist.length; i++) {
        let trans = eval(tlist[i]);
        res = trans.v_compute(res)
      }
      return res
    """
    transforms=[t for t in transforms if t is not None]
    arg_dict = dict([("t" + str(i), trans) for i, trans in enumerate(transforms)])
    arg_dict["tlist"] = ["t" + str(i) for i in range(len(transforms))]
    return CustomJSTransform(func=composite_transform_func,v_func=composite_transform_v_func,args=arg_dict)


def composite_transform(field: str, *transforms: Transform):
    """ Like bokeh.transform.transform except takes multiple arbitrary transformations instead of one"""
    return transform(field,compose_transforms(*transforms))
