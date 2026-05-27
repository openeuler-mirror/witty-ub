#include "urma_failure_625.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure625> g_urma("urma_625");

bool UrmaFailure625::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfr_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfr not from the same dev, cannot delete in a batch, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure625::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure625::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure625::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure625::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure625::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfr_batch，jfr not from the same dev, cannot delete in a batch, "
           "index:";
}

std::string UrmaFailure625::GetId() const
{
    return "urma_625";
}

} // namespace diag
