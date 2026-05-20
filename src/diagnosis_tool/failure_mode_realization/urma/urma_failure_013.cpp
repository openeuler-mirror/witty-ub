#include "urma_failure_013.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure013> g_urma("urma_013");

bool UrmaFailure013::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_import_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Multi-path jetty only support RM or RC, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure013::GetName() const
{
    return "bondp_import_jetty 校验 Jetty 业务条件不满足导致导入流程拒绝继续执行";
}

std::string UrmaFailure013::GetRootCauseDesc() const
{
    return "bondp_import_jetty 在执行导入时发现 Jetty "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure013::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure013::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure013::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Multi-path jetty only support RM or RC, trans_mode";
}

std::string UrmaFailure013::GetId() const
{
    return "urma_013";
}

} // namespace diag
