#include "urma_failure_053.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure053> g_urma("urma_053");

bool UrmaFailure053::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("Failed to alloc target jetty") != std::string::npos;
}

std::string UrmaFailure053::GetName() const
{
    return "bondparget jetty分配失败导致导入Jetty失败";
}

std::string UrmaFailure053::GetRootCauseDesc() const
{
    return "bondp_import_jetty执行导入Jetty前需要准备bondparget jetty，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure053::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure053::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure053::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，Failed to alloc target jetty。";
}

std::string UrmaFailure053::GetId() const
{
    return "urma_053";
}
} // namespace diag
