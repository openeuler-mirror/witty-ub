#include "urma_failure_106.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure106> g_urma("urma_106");

bool UrmaFailure106::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_relink_primary_import' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to unimport old primary ptjetty, lidx:' | grep -F 'tidx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure106::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure106::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure106::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure106::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure106::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_relink_primary_import，Failed to unimport old primary ptjetty, "
           "lidx:，tidx:";
}

std::string UrmaFailure106::GetId() const
{
    return "urma_106";
}

} // namespace diag
