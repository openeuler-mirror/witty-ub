#include "urma_failure_245.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure245> g_urma("urma_245");

bool UrmaFailure245::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Initialized already'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure245::GetName() const
{
    return "bondp_init 校验 context 业务条件不满足导致初始化流程拒绝继续执行";
}

std::string UrmaFailure245::GetRootCauseDesc() const
{
    return "bondp_init 在执行初始化时发现 context "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure245::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure245::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure245::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Initialized already";
}

std::string UrmaFailure245::GetId() const
{
    return "urma_245";
}

} // namespace diag
