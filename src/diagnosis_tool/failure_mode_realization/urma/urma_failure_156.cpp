#include "urma_failure_156.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure156> g_urma("urma_156");

bool UrmaFailure156::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_rebuild_local_pjetty") != std::string::npos &&
           message.find("Failed to recreate pjetty at idx:") != std::string::npos;
}

std::string UrmaFailure156::GetName() const
{
    return "下层资源创建失败导致rebuildrebuild、local、pjetty失败";
}

std::string UrmaFailure156::GetRootCauseDesc() const
{
    return "bondp_rebuild_local_"
           "pjetty在rebuildrebuild、local、pjetty过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立"
           "。";
}

RootCause UrmaFailure156::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure156::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure156::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_rebuild_local_pjetty，Failed to recreate pjetty at idx:。";
}

std::string UrmaFailure156::GetId() const
{
    return "urma_156";
}
} // namespace diag
