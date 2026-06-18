#include "urma_failure_507.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure507> g_urma("urma_507");

bool UrmaFailure507::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfr") != std::string::npos &&
           message.find("Failed to delete_vjfr") != std::string::npos;
}

std::string UrmaFailure507::GetName() const
{
    return "下层资源删除失败导致删除JFR失败";
}

std::string UrmaFailure507::GetRootCauseDesc() const
{
    return "bondp_delete_jfr清理JFR时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure507::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure507::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure507::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfr，Failed to delete_vjfr。";
}

std::string UrmaFailure507::GetId() const
{
    return "urma_507";
}
} // namespace diag
