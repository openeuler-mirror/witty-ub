#include "urma_failure_154.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure154> g_urma("urma_154");

bool UrmaFailure154::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_health_check_ctx") != std::string::npos &&
           message.find("Failed to create health_check_fd, errno:") != std::string::npos;
}

std::string UrmaFailure154::GetName() const
{
    return "下层资源创建失败导致创建health、context失败";
}

std::string UrmaFailure154::GetRootCauseDesc() const
{
    return "bondp_create_health_check_"
           "ctx在创建health、context过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure154::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure154::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure154::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_health_check_ctx，Failed to create health_check_fd, "
           "errno:。";
}

std::string UrmaFailure154::GetId() const
{
    return "urma_154";
}
} // namespace diag
