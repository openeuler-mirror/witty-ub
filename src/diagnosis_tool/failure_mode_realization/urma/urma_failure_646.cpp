#include "urma_failure_646.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure646> g_urma("urma_646");

bool UrmaFailure646::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfc is deactived, can not delete.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure646::GetName() const
{
    return "JFC清理阶段下层释放操作失败";
}

std::string UrmaFailure646::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure646::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure646::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure646::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfc，jfc is deactived, can not delete.";
}

std::string UrmaFailure646::GetId() const
{
    return "urma_646";
}

} // namespace diag
