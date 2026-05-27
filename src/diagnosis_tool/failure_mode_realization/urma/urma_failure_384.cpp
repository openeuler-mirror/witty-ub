#include "urma_failure_384.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure384> g_urma("urma_384");

bool UrmaFailure384::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc memory.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure384::GetName() const
{
    return "JFC相关临时结构或命令参数分配失败";
}

std::string UrmaFailure384::GetRootCauseDesc() const
{
    return "函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure384::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure384::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure384::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfc_batch，Failed to alloc memory.";
}

std::string UrmaFailure384::GetId() const
{
    return "urma_384";
}

} // namespace diag
