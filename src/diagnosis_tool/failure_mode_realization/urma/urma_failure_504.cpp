#include "urma_failure_504.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure504> g_urma("urma_504");

bool UrmaFailure504::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pjfr") != std::string::npos &&
           message.find("Failed to delete pjfr") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure504::GetName() const
{
    return "下层资源删除失败导致删除物理JFR失败";
}

std::string UrmaFailure504::GetRootCauseDesc() const
{
    return "bondp_delete_pjfr清理物理JFR时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure504::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure504::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure504::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfr，Failed to delete pjfr，, ret:。";
}

std::string UrmaFailure504::GetId() const
{
    return "urma_504";
}
} // namespace diag
