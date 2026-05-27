#include "urma_failure_391.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure391> g_urma("urma_391");

bool UrmaFailure391::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'failed to exec ops->alloc_jfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure391::GetName() const
{
    return "JFC相关临时结构或命令参数分配失败";
}

std::string UrmaFailure391::GetRootCauseDesc() const
{
    return "函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure391::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure391::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure391::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfc，failed to exec ops->alloc_jfc。";
}

std::string UrmaFailure391::GetId() const
{
    return "urma_391";
}

} // namespace diag
