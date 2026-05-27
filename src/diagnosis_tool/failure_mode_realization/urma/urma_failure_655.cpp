#include "urma_failure_655.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure655> g_urma("urma_655");

bool UrmaFailure655::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to free jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure655::GetName() const
{
    return "JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure655::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure655::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure655::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure655::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jfs，Failed to free jfs.";
}

std::string UrmaFailure655::GetId() const
{
    return "urma_655";
}

} // namespace diag
