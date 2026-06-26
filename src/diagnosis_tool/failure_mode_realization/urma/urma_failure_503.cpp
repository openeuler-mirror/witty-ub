#include "urma_failure_503.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure503> g_urma("urma_503");

bool UrmaFailure503::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfs") != std::string::npos &&
           message.find("Failed to delete pjfs") != std::string::npos;
}

std::string UrmaFailure503::GetName() const
{
    return "下层资源删除失败导致删除JFS失败";
}

std::string UrmaFailure503::GetRootCauseDesc() const
{
    return "bondp_delete_jfs清理JFS时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure503::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure503::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure503::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfs，Failed to delete pjfs。";
}

std::string UrmaFailure503::GetId() const
{
    return "urma_503";
}
} // namespace diag
