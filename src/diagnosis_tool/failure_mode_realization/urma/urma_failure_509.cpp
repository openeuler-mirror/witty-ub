#include "urma_failure_509.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure509> g_urma("urma_509");

bool UrmaFailure509::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pjetty") != std::string::npos &&
           message.find("Failed to delete pjetty") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure509::GetName() const
{
    return "下层资源删除失败导致删除pjetty失败";
}

std::string UrmaFailure509::GetRootCauseDesc() const
{
    return "bondp_delete_pjetty清理pjetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure509::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure509::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure509::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjetty，Failed to delete pjetty，, ret:。";
}

std::string UrmaFailure509::GetId() const
{
    return "urma_509";
}
} // namespace diag
