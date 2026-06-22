#include "urma_failure_192.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure192> g_urma("urma_192");

bool UrmaFailure192::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfs") != std::string::npos &&
           message.find("jfs cfg out of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos && message.find(", inline_data:") != std::string::npos &&
           message.find(", max_inline_len:") != std::string::npos && message.find(", sge:") != std::string::npos &&
           message.find(", max_sge:") != std::string::npos && message.find(", rsge:") != std::string::npos &&
           message.find(", max_rsge:") != std::string::npos;
}

std::string UrmaFailure192::GetName() const
{
    return "JFS配置值超过设备能力导致分配JFS失败";
}

std::string UrmaFailure192::GetRootCauseDesc() const
{
    return "urma_alloc_jfs会按设备能力校验JFS配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure192::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure192::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure192::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfs，jfs cfg out of range, depth:，, max_depth:，, "
           "inline_data:，, max"
           "_inline_len:，, sge:，, max_sge:，, rsge:，, max_rsge:。";
}

std::string UrmaFailure192::GetId() const
{
    return "urma_192";
}
} // namespace diag
