#include "kvcache_conn_fault_002_004.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_004 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250)
static AutoRegister<KvcacheConnFault002_004> g_kvcacheconnfault002_004("kvcache_conn_fault_002_004");

bool KvcacheConnFault002_004::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && grep 'OBJECT_KEYS_MAX_SIZE_LIMIT' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG $WITTY_UB_CLIENT_INFO_LOG $WITTY_UB_WORKER_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_004::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250
    return "respMsg批次超限故障";
}

std::string KvcacheConnFault002_004::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250
    return "批处理大小超过最大限制，属于用户侧问题。（来源：08手册:L250）";
}

RootCause KvcacheConnFault002_004::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_004::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250
    return "拆分批次，减小单次请求的对象数量。（来源：08手册:L250）";
}

std::string KvcacheConnFault002_004::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L185, L187, L250
    return "通过日志关键字识别（来源：08手册:L250）：匹配OBJECT_KEYS_MAX_SIZE_LIMIT。（来源：08手册:L250）";
}

std::string KvcacheConnFault002_004::GetId() const
{
    return "kvcache_conn_fault_002_004";
}

} // namespace diag
