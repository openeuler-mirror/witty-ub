#include "urma_failure_499.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure499> g_urma("urma_499");

bool UrmaFailure499::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pjfs") != std::string::npos &&
           message.find("Failed to delete pjfs") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure499::GetName() const
{
    return "下层资源删除失败导致删除物理JFS失败";
}

std::string UrmaFailure499::GetRootCauseDesc() const
{
    return "bondp_delete_pjfs清理物理JFS时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure499::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure499::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure499::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfs，Failed to delete pjfs，, ret:。";
}

std::string UrmaFailure499::GetId() const
{
    return "urma_499";
}
} // namespace diag
