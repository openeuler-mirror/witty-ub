#include "urma_failure_297.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure297> g_urma("urma_297");

bool UrmaFailure297::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_health_ctx_global") != std::string::npos &&
           message.find("Failed to alloc health ctx node") != std::string::npos;
}

std::string UrmaFailure297::GetName() const
{
    return "bondp health ctx node分配失败导致注册health、context、global失败";
}

std::string UrmaFailure297::GetRootCauseDesc() const
{
    return "bondp_register_health_ctx_global执行注册health、context、global前需要准备bondp health ctx "
           "node，内存或资源分配失败会阻断后续URMA"
           "操作。";
}

RootCause UrmaFailure297::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure297::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure297::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_health_ctx_global，Failed to alloc health ctx node。";
}

std::string UrmaFailure297::GetId() const
{
    return "urma_297";
}
} // namespace diag
