#include "urma_failure_641.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure641> g_urma("urma_641");

bool UrmaFailure641::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfc_batch' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'jfc not from the same dev, cannot delete in a batch, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure641::GetName() const
{
    return "JFC清理阶段下层释放操作失败";
}

std::string UrmaFailure641::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure641::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure641::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure641::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，jfc not from the same dev, cannot delete in "
           "a batch, index:。";
}

std::string UrmaFailure641::GetId() const
{
    return "urma_641";
}

} // namespace diag
