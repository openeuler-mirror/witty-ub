#include "urma_failure_515.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure515> g_urma("urma_515");

bool UrmaFailure515::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_rebuild_local_pjetty") != std::string::npos &&
           message.find("Failed to delete pjetty at idx:") != std::string::npos;
}

std::string UrmaFailure515::GetName() const
{
    return "下层资源删除失败导致rebuildrebuild、local、pjetty失败";
}

std::string UrmaFailure515::GetRootCauseDesc() const
{
    return "bondp_rebuild_local_"
           "pjetty清理rebuild、local、pjetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure515::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure515::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure515::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_rebuild_local_pjetty，Failed to delete pjetty at idx:。";
}

std::string UrmaFailure515::GetId() const
{
    return "urma_515";
}
} // namespace diag
