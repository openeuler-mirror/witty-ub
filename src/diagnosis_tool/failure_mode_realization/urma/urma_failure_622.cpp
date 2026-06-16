#include "urma_failure_622.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure622> g_urma("urma_622");

bool UrmaFailure622::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'jfs not from the same dev, cannot delete in a batch, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure622::GetName() const
{
    return "JFS清理阶段下层释放操作失败";
}

std::string UrmaFailure622::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure622::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure622::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure622::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，jfs not from the same dev, cannot delete in "
           "a batch, index:。";
}

std::string UrmaFailure622::GetId() const
{
    return "urma_622";
}

} // namespace diag
