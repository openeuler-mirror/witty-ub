#include "urma_failure_512.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure512> g_urma("urma_512");

bool UrmaFailure512::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc bondp segment comp'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure512::GetName() const
{
    return "Segment相关临时结构或命令参数分配失败";
}

std::string UrmaFailure512::GetRootCauseDesc() const
{
    return "函数在分配Segment前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure512::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure512::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure512::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vseg，Failed to alloc bondp segment comp";
}

std::string UrmaFailure512::GetId() const
{
    return "urma_512";
}

} // namespace diag
