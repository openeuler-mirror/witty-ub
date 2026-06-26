#include "urma_failure_252.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure252> g_urma("urma_252");

bool UrmaFailure252::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_dev_cap") != std::string::npos &&
           message.find("jetty cfg out of range, jfs_depth:") != std::string::npos &&
           message.find(", max_jfs_depth:") != std::string::npos &&
           message.find(", inline_data:") != std::string::npos &&
           message.find(", max_jfs_inline_len:") != std::string::npos &&
           message.find(", jfr_depth:") != std::string::npos && message.find(", max_jfr_depth:") != std::string::npos &&
           message.find(", jfs_sge:") != std::string::npos && message.find(", max_jfs_sge:") != std::string::npos &&
           message.find(", jfs_rsge:") != std::string::npos && message.find(", max_jfs_rsge:") != std::string::npos &&
           message.find(", jfr_sge:") != std::string::npos && message.find(", max_jfr_sge:") != std::string::npos;
}

std::string UrmaFailure252::GetName() const
{
    return "Jetty、设备、能力信息配置值超过设备能力导致创建Jetty、设备、能力信息失败";
}

std::string UrmaFailure252::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_dev_cap会按设备能力校验Jetty、设备、能力信息配置，深度、数量或索引超过硬件/"
           "驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure252::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure252::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure252::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_dev_cap，jetty cfg out of range, jfs_depth:，, "
           "max_jfs_"
           "depth:，, inline_data:，, max_jfs_inline_len:，, jfr_depth:，, max_jfr_depth:，, jfs_sge:，, "
           "max_jfs_sge:，, "
           "jfs_rsge:，, max_jfs_rsge:，, jfr_sge:，, max_jfr_sge:。";
}

std::string UrmaFailure252::GetId() const
{
    return "urma_252";
}
} // namespace diag
