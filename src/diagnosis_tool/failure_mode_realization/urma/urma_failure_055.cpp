#include "urma_failure_055.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure055> g_urma("urma_055");

bool UrmaFailure055::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("RM jetty import requires drv_ext.vjetty.") != std::string::npos;
}

std::string UrmaFailure055::GetName() const
{
    return "Jetty状态不满足要求导致导入Jetty失败";
}

std::string UrmaFailure055::GetRootCauseDesc() const
{
    return "bondp_import_jetty执行导入Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure055::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure055::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure055::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，RM jetty import requires drv_ext.vjetty.。";
}

std::string UrmaFailure055::GetId() const
{
    return "urma_055";
}
} // namespace diag
