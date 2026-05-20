#include "urma_failure_838.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure838> g_urma("urma_838");

bool UrmaFailure838::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_add_jfr_p_vjetty_id_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add p_vjfr_id[' | "
        "grep -F ']: ret:' | "
        "grep -F ', p_jfr_id:' | "
        "grep -F ', v_jfr_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure838::GetName() const
{
    return "bondp_add_jfr_p_vjetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure838::GetRootCauseDesc() const
{
    return "bondp_add_jfr_p_vjetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure838::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure838::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure838::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to add p_vjfr_id[]: ret: , p_jfr_id: , v_jfr_id";
}

std::string UrmaFailure838::GetId() const
{
    return "urma_838";
}

} // namespace diag
