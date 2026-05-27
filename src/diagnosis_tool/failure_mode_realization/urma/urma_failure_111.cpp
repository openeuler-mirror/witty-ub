#include "urma_failure_111.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure111> g_urma("urma_111");

bool UrmaFailure111::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_rebuild_local_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete pjetty at idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure111::GetName() const
{
    return "物理 Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure111::GetRootCauseDesc() const
{
    return "函数负责释放或撤销物理 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure111::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure111::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure111::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_rebuild_local_pjetty，Failed to delete pjetty at idx:";
}

std::string UrmaFailure111::GetId() const
{
    return "urma_111";
}

} // namespace diag
