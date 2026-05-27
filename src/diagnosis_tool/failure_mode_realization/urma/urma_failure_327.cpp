#include "urma_failure_327.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure327> g_urma("urma_327");

bool UrmaFailure327::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vjfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ubcore create jfs failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure327::GetName() const
{
    return "JFS创建时下层资源准备失败";
}

std::string UrmaFailure327::GetRootCauseDesc() const
{
    return "函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure327::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure327::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure327::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vjfs，ubcore create jfs failed.";
}

std::string UrmaFailure327::GetId() const
{
    return "urma_327";
}

} // namespace diag
