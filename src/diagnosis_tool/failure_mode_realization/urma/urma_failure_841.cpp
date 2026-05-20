#include "urma_failure_841.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure841> g_urma("urma_841");

bool UrmaFailure841::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_add_jetty_p_vjetty_id_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add p_vjetty_id[' | "
        "grep -F ']: ret:' | "
        "grep -F ', p_jetty_id:' | "
        "grep -F ', v_jetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure841::GetName() const
{
    return "bondp_add_jetty_p_vjetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure841::GetRootCauseDesc() const
{
    return "bondp_add_jetty_p_vjetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure841::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure841::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure841::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to add p_vjetty_id[]: ret: , p_jetty_id: , v_jetty_id";
}

std::string UrmaFailure841::GetId() const
{
    return "urma_841";
}

} // namespace diag
