#include "urma_failure_133.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure133> g_urma("urma_133");

bool UrmaFailure133::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_add_jfs_p_vjetty_id_info") != std::string::npos &&
           message.find("Failed to add p_vjfs_id[") != std::string::npos &&
           message.find("]: ret:") != std::string::npos && message.find(", p_jfs_id:") != std::string::npos &&
           message.find(", v_jfs_id:") != std::string::npos;
}

std::string UrmaFailure133::GetName() const
{
    return "添加JFS、vjetty、ID执行失败导致添加JFS、vjetty、ID失败";
}

std::string UrmaFailure133::GetRootCauseDesc() const
{
    return "bondp_add_jfs_p_vjetty_id_"
           "info执行添加JFS、vjetty、ID时依赖的添加JFS、vjetty、ID步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure133::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure133::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure133::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_add_jfs_p_vjetty_id_info，Failed to add p_vjfs_id[，]: ret:，, "
           "p_jfs_id:，,"
           " v_jfs_id:。";
}

std::string UrmaFailure133::GetId() const
{
    return "urma_133";
}
} // namespace diag
