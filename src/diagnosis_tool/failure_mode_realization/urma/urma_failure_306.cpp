#include "urma_failure_306.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure306> g_urma("urma_306");

bool UrmaFailure306::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_health_check_ctx") != std::string::npos &&
           message.find("Failed to register health ctx globally") != std::string::npos;
}

std::string UrmaFailure306::GetName() const
{
    return "下层注册或导入返回失败导致创建health、context失败";
}

std::string UrmaFailure306::GetRootCauseDesc() const
{
    return "bondp_create_health_check_"
           "ctx在创建health、context时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure306::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure306::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure306::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_health_check_ctx，Failed to register health ctx globally。";
}

std::string UrmaFailure306::GetId() const
{
    return "urma_306";
}
} // namespace diag
