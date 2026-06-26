#include "urma_failure_716.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure716> g_urma("urma_716");

bool UrmaFailure716::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfs") != std::string::npos &&
           message.find("jfs cfg out of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos && message.find(", inline_data:") != std::string::npos &&
           message.find(", max_inline_len:") != std::string::npos && message.find(", sge:") != std::string::npos &&
           message.find(", max_sge:") != std::string::npos && message.find(", rsge:") != std::string::npos &&
           message.find(", max_rsge:") != std::string::npos;
}

std::string UrmaFailure716::GetName() const
{
    return "JFS配置值超过设备能力导致激活JFS失败";
}

std::string UrmaFailure716::GetRootCauseDesc() const
{
    return "urma_active_jfs会按设备能力校验JFS配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure716::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure716::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure716::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，jfs cfg out of range, depth:，, max_depth:，, "
           "inline_data:，, ma"
           "x_inline_len:，, sge:，, max_sge:，, rsge:，, max_rsge:。";
}

std::string UrmaFailure716::GetId() const
{
    return "urma_716";
}
} // namespace diag
