#include "urma_failure_064.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure064> g_urma("urma_064");

bool UrmaFailure064::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jfr") != std::string::npos &&
           message.find("RM jfr import requires drv_ext.vjfs") != std::string::npos;
}

std::string UrmaFailure064::GetName() const
{
    return "JFR状态不满足要求导致导入JFR失败";
}

std::string UrmaFailure064::GetRootCauseDesc() const
{
    return "bondp_import_jfr执行导入JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure064::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure064::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure064::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jfr，RM jfr import requires drv_ext.vjfs。";
}

std::string UrmaFailure064::GetId() const
{
    return "urma_064";
}
} // namespace diag
