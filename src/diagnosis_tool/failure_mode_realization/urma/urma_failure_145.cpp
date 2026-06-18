#include "urma_failure_145.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure145> g_urma("urma_145");

bool UrmaFailure145::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_add_jetty_p_vjetty_id_info") != std::string::npos &&
           message.find("Failed to add p_vjetty_id[") != std::string::npos &&
           message.find("]: ret:") != std::string::npos && message.find(", p_jetty_id:") != std::string::npos &&
           message.find(", v_jetty_id:") != std::string::npos;
}

std::string UrmaFailure145::GetName() const
{
    return "添加Jetty、vjetty、ID执行失败导致添加Jetty、vjetty、ID失败";
}

std::string UrmaFailure145::GetRootCauseDesc() const
{
    return "bondp_add_jetty_p_vjetty_id_"
           "info执行添加Jetty、vjetty、ID时依赖的添加Jetty、vjetty、ID步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure145::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure145::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure145::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_add_jetty_p_vjetty_id_info，Failed to add p_vjetty_id[，]: "
           "ret:，, p_jetty"
           "_id:，, v_jetty_id:。";
}

std::string UrmaFailure145::GetId() const
{
    return "urma_145";
}
} // namespace diag
