#include "urma_failure_502.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure502> g_urma("urma_502");

bool UrmaFailure502::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfs") != std::string::npos &&
           message.find("Failed to delete vjfs") != std::string::npos;
}

std::string UrmaFailure502::GetName() const
{
    return "下层资源删除失败导致删除JFS失败";
}

std::string UrmaFailure502::GetRootCauseDesc() const
{
    return "bondp_delete_jfs清理JFS时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure502::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure502::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure502::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfs，Failed to delete vjfs。";
}

std::string UrmaFailure502::GetId() const
{
    return "urma_502";
}
} // namespace diag
