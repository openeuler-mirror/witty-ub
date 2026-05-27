#include "urma_failure_038.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure038> g_urma("urma_038");

bool UrmaFailure038::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'failed to init alloc jetty cmd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure038::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure038::GetRootCauseDesc() const
{
    return "函数在初始化Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure038::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure038::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure038::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_alloc_jetty，failed to init alloc jetty cmd";
}

std::string UrmaFailure038::GetId() const
{
    return "urma_038";
}

} // namespace diag
