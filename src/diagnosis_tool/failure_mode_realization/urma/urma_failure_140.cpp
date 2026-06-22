#include "urma_failure_140.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure140> g_urma("urma_140");

bool UrmaFailure140::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_add_jfr_p_vjetty_id_info") != std::string::npos &&
           message.find("Failed to add p_vjfr_id[") != std::string::npos &&
           message.find("]: ret:") != std::string::npos && message.find(", p_jfr_id:") != std::string::npos &&
           message.find(", v_jfr_id:") != std::string::npos;
}

std::string UrmaFailure140::GetName() const
{
    return "添加JFR、vjetty、ID执行失败导致添加JFR、vjetty、ID失败";
}

std::string UrmaFailure140::GetRootCauseDesc() const
{
    return "bondp_add_jfr_p_vjetty_id_"
           "info执行添加JFR、vjetty、ID时依赖的添加JFR、vjetty、ID步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure140::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure140::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure140::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_add_jfr_p_vjetty_id_info，Failed to add p_vjfr_id[，]: ret:，, "
           "p_jfr_id:，,"
           " v_jfr_id:。";
}

std::string UrmaFailure140::GetId() const
{
    return "urma_140";
}
} // namespace diag
