#include "urma_failure_388.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure388> g_urma("urma_388");

bool UrmaFailure388::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'failed to exec ops->alloc_jfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure388::GetName() const
{
    return "JFC相关临时结构或命令参数分配失败";
}

std::string UrmaFailure388::GetRootCauseDesc() const
{
    return "函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure388::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure388::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure388::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfc，failed to exec ops->alloc_jfc";
}

std::string UrmaFailure388::GetId() const
{
    return "urma_388";
}

} // namespace diag
