#include "urma_failure_303.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure303> g_urma("urma_303");

bool UrmaFailure303::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_unimport_health_check_tseg") != std::string::npos &&
           message.find("Failed to unimport health check seg (") != std::string::npos &&
           message.find(",") != std::string::npos && message.find(")") != std::string::npos;
}

std::string UrmaFailure303::GetName() const
{
    return "下层注册或导入返回失败导致取消导入health、TSEG失败";
}

std::string UrmaFailure303::GetRootCauseDesc() const
{
    return "bondp_unimport_health_check_"
           "tseg在取消导入health、TSEG时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure303::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure303::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure303::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_health_check_tseg，Failed to unimport health check seg "
           "(，,，)。";
}

std::string UrmaFailure303::GetId() const
{
    return "urma_303";
}
} // namespace diag
