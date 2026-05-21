#include "urma_failure_192.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure192> g_urma("urma_192");

bool UrmaFailure192::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'UB device must use shared jfr when create jetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure192::GetName() const
{
    return "bondp_create_jetty 执行创建 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure192::GetRootCauseDesc() const
{
    return "bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure192::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure192::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure192::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：UB device must use shared jfr when create jetty";
}

std::string UrmaFailure192::GetId() const
{
    return "urma_192";
}

} // namespace diag
