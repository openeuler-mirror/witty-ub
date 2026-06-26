#include "urma_failure_189.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure189> g_urma("urma_189");

bool UrmaFailure189::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfs") != std::string::npos &&
           message.find("jfs cfg out of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos && message.find(", inline_data:") != std::string::npos &&
           message.find(", max_inline_len:") != std::string::npos && message.find(", sge:") != std::string::npos &&
           message.find(", max_sge:") != std::string::npos && message.find(", rsge:") != std::string::npos &&
           message.find(", max_rsge:") != std::string::npos;
}

std::string UrmaFailure189::GetName() const
{
    return "JFS配置值超过设备能力导致创建JFS失败";
}

std::string UrmaFailure189::GetRootCauseDesc() const
{
    return "urma_create_jfs会按设备能力校验JFS配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure189::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure189::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure189::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfs，jfs cfg out of range, depth:，, max_depth:，, "
           "inline_data:，, ma"
           "x_inline_len:，, sge:，, max_sge:，, rsge:，, max_rsge:。";
}

std::string UrmaFailure189::GetId() const
{
    return "urma_189";
}
} // namespace diag
