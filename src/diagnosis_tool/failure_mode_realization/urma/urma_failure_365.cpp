#include "urma_failure_365.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure365> g_urma("urma_365");

bool UrmaFailure365::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to malloc buffer.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure365::GetName() const
{
    return "JFS相关临时结构或命令参数分配失败";
}

std::string UrmaFailure365::GetRootCauseDesc() const
{
    return "函数在删除JFS前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure365::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure365::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure365::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfs_batch，Failed to malloc buffer.";
}

std::string UrmaFailure365::GetId() const
{
    return "urma_365";
}

} // namespace diag
