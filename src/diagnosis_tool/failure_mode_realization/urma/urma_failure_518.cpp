#include "urma_failure_518.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure518> g_urma("urma_518");

bool UrmaFailure518::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc target seg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure518::GetName() const
{
    return "Segment相关临时结构或命令参数分配失败";
}

std::string UrmaFailure518::GetRootCauseDesc() const
{
    return "函数在分配Segment前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure518::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure518::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure518::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pseg，Failed to alloc target seg";
}

std::string UrmaFailure518::GetId() const
{
    return "urma_518";
}

} // namespace diag
