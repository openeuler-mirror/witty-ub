#include "urma_failure_026.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure026> g_urma("urma_026");

bool UrmaFailure026::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_uninit") != std::string::npos &&
           message.find("Failed to delete global context.") != std::string::npos;
}

std::string UrmaFailure026::GetName() const
{
    return "下层资源删除失败导致uninituninit失败";
}

std::string UrmaFailure026::GetRootCauseDesc() const
{
    return "bondp_uninit清理uninit时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure026::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure026::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure026::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_uninit，Failed to delete global context.。";
}

std::string UrmaFailure026::GetId() const
{
    return "urma_026";
}
} // namespace diag
